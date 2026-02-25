import re
from difflib import SequenceMatcher
from html import unescape
from itertools import combinations

from sqlalchemy import text
from sqlalchemy import func

from ..extensions import db
from ..knowledge_base import get_recommendation_score
from ..models import GlobalOrganization, GoSimilarity, OrgMapping


STOP_WORDS = {
    "the", "of", "for", "and", "in", "to", "a", "an", "at", "on", "&",
    "de", "del", "y", "et", "la", "le", "les", "el", "los", "las",
}


def normalize_name(name: str) -> str:
    if not name:
        return ""
    name = unescape(name)
    name = name.lower()
    name = re.sub(r"[^\w\s]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    words = [w for w in name.split() if w and w not in STOP_WORDS]
    return " ".join(words)


def token_set(norm: str) -> set[str]:
    if not norm:
        return set()
    return set(norm.split())


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    if inter == 0:
        return 0.0
    union = len(a | b)
    return inter / union if union else 0.0


def weighted_similarity(
    norm1: str,
    tok1: set[str],
    acr1: str,
    norm2: str,
    tok2: set[str],
    acr2: str,
    original1: str = "",
    original2: str = "",
) -> float:
    if not norm1 or not norm2:
        return 0.0

    if norm1 == norm2:
        orig1_clean = original1.lower().strip() if original1 else norm1
        orig2_clean = original2.lower().strip() if original2 else norm2
        if orig1_clean == orig2_clean:
            return 100.0
        orig_sim = SequenceMatcher(None, orig1_clean, orig2_clean).ratio() * 100.0
        return min(orig_sim, 98.0)

    seq_sim = SequenceMatcher(None, norm1, norm2).ratio() * 100.0
    token_sim = jaccard(tok1, tok2) * 100.0
    acronym_sim = 100.0 if (acr1 and acr2 and acr1 == acr2) else 0.0

    if acronym_sim == 100.0:
        final_sim = 75.0 + (seq_sim * 0.15) + (token_sim * 0.10)
    else:
        final_sim = (seq_sim * 0.5) + (token_sim * 0.3) + (acronym_sim * 0.2)

    return min(final_sim, 100.0)


def compute_similarity_edges(threshold=70.0, max_bucket=250):
    gos = [
        {
            "global_org_id": go.global_org_id,
            "global_org_name": go.global_org_name,
            "global_acronym": go.global_acronym,
        }
        for go in GlobalOrganization.query.order_by(GlobalOrganization.global_org_id.asc()).all()
    ]

    for go in gos:
        norm = normalize_name(go.get("global_org_name") or "")
        go["norm"] = norm
        go["tok"] = token_set(norm)
        go["acr"] = (go.get("global_acronym") or "").upper().strip()

    buckets = {}
    for idx, go in enumerate(gos):
        keys = set()
        acr = go["acr"]
        if acr and 2 <= len(acr) <= 12:
            keys.add(f"acr:{acr}")

        words = (go["norm"] or "").split()
        if words:
            keys.add(f"t0:{words[0]}")
            keys.add(f"p3:{words[0][:3]}")
            if len(words) >= 2:
                keys.add(f"t01:{words[0]}_{words[1]}")

        if go["tok"]:
            shortest = min(go["tok"], key=len)
            if len(shortest) >= 4:
                keys.add(f"sh:{shortest[:4]}")

        for key in keys:
            buckets.setdefault(key, []).append(idx)

    seen_pairs = set()
    candidate_pairs = []
    for _, idxs in buckets.items():
        if len(idxs) < 2:
            continue
        if len(idxs) > max_bucket:
            continue
        for a, b in combinations(idxs, 2):
            id1 = gos[a]["global_org_id"]
            id2 = gos[b]["global_org_id"]
            lo, hi = (id1, id2) if id1 < id2 else (id2, id1)
            pair_key = (lo, hi)
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)
            candidate_pairs.append((a, b))

    edges = []
    for a, b in candidate_pairs:
        go1 = gos[a]
        go2 = gos[b]

        jac = jaccard(go1["tok"], go2["tok"])
        if jac < 0.10 and not (go1["acr"] and go2["acr"] and go1["acr"] == go2["acr"]):
            continue

        sim = weighted_similarity(
            go1["norm"],
            go1["tok"],
            go1["acr"],
            go2["norm"],
            go2["tok"],
            go2["acr"],
            go1.get("global_org_name", ""),
            go2.get("global_org_name", ""),
        )
        if sim >= threshold:
            edges.append((go1["global_org_id"], go2["global_org_id"], round(sim, 2)))

    return edges


def recalculate_similarity_table(threshold=70.0, max_bucket=250):
    db.session.execute(text("DELETE FROM go_similarity"))
    edges = compute_similarity_edges(threshold=threshold, max_bucket=max_bucket)

    rows = []
    for source_id, target_id, score in edges:
        rows.append(
            {
                "source_global_org_id": source_id,
                "target_global_org_id": target_id,
                "similarity_percent": score,
            }
        )
        rows.append(
            {
                "source_global_org_id": target_id,
                "target_global_org_id": source_id,
                "similarity_percent": score,
            }
        )

    if rows:
        db.session.bulk_insert_mappings(GoSimilarity, rows)
    db.session.commit()
    return len(edges)


def refresh_usage_counts():
    counts = (
        db.session.query(OrgMapping.global_org_id, func.count(OrgMapping.id))
        .group_by(OrgMapping.global_org_id)
        .all()
    )
    count_map = {go_id: count for go_id, count in counts}
    all_gos = GlobalOrganization.query.all()
    for go in all_gos:
        go.usage_count = count_map.get(go.global_org_id, 0)
    db.session.commit()


def build_go_summary_response():
    similarities = GoSimilarity.query.all()
    go_groups = {}
    groups = {}
    next_group_id = 1

    for item in similarities:
        source_id = item.source_global_org_id
        target_id = item.target_global_org_id
        source_group = go_groups.get(source_id)
        target_group = go_groups.get(target_id)

        if source_group is None and target_group is None:
            go_groups[source_id] = next_group_id
            go_groups[target_id] = next_group_id
            groups[next_group_id] = {source_id, target_id}
            next_group_id += 1
        elif source_group is None:
            go_groups[source_id] = target_group
            groups[target_group].add(source_id)
        elif target_group is None:
            go_groups[target_id] = source_group
            groups[source_group].add(target_id)
        elif source_group != target_group:
            for go_id in groups[target_group]:
                go_groups[go_id] = source_group
                groups[source_group].add(go_id)
            del groups[target_group]

    duplicate_groups = []
    grouped_ids = set()

    for group_id, go_ids in groups.items():
        if len(go_ids) < 2:
            continue

        go_list = GlobalOrganization.query.filter(GlobalOrganization.global_org_id.in_(list(go_ids))).all()
        members = []
        total_instances = 0
        max_similarity = 0.0

        pair_scores = GoSimilarity.query.filter(
            GoSimilarity.source_global_org_id.in_(list(go_ids)),
            GoSimilarity.target_global_org_id.in_(list(go_ids)),
        ).all()
        if pair_scores:
            max_similarity = max(float(x.similarity_percent) for x in pair_scores if x.similarity_percent is not None)

        for go in go_list:
            usage = go.usage_count or 0
            total_instances += usage
            instance_orgs = (
                OrgMapping.query.filter_by(global_org_id=go.global_org_id)
                .with_entities(
                    OrgMapping.instance_org_id,
                    OrgMapping.instance_org_name,
                    OrgMapping.instance_org_acronym,
                    OrgMapping.instance_org_type,
                    OrgMapping.fund_name,
                    OrgMapping.match_percent,
                )
                .limit(20)
                .all()
            )
            item = {
                "global_org_id": go.global_org_id,
                "global_org_name": go.global_org_name,
                "global_org_acronym": go.global_acronym or "",
                "usage_count": usage,
                "name_length": len(go.global_org_name or ""),
                "instance_organizations": [
                    {
                        "instance_org_id": row[0],
                        "instance_org_name": row[1],
                        "instance_org_acronym": row[2],
                        "instance_org_type": row[3],
                        "fund_name": row[4],
                        "match_percent": float(row[5]) if row[5] is not None else None,
                    }
                    for row in instance_orgs
                ],
            }
            rec = get_recommendation_score(item["global_org_name"], item["usage_count"])
            item["recommendation_score"] = rec["score"]
            item["kb_match"] = rec["kb_match"]
            item["kb_standard_name"] = rec.get("standard_name")
            members.append(item)

        recommended = max(members, key=lambda x: x["recommendation_score"])
        for m in members:
            m["is_recommended"] = m["global_org_id"] == recommended["global_org_id"]
            grouped_ids.add(m["global_org_id"])
        members.sort(key=lambda x: (not x["is_recommended"], -x["usage_count"]))

        duplicate_groups.append(
            {
                "group_id": group_id,
                "group_name": f"{recommended['global_org_name']} Group",
                "max_similarity": max_similarity,
                "total_members": len(members),
                "total_instances": total_instances,
                "recommended_master": {
                    "global_org_id": recommended["global_org_id"],
                    "global_org_name": recommended["global_org_name"],
                    "global_org_acronym": recommended["global_org_acronym"],
                    "usage_count": recommended["usage_count"],
                },
                "members": members,
            }
        )

    duplicate_groups.sort(key=lambda x: -x["max_similarity"])

    unique_organizations = []
    for go in GlobalOrganization.query.all():
        if go.global_org_id in grouped_ids:
            continue
        instance_orgs = (
            OrgMapping.query.filter_by(global_org_id=go.global_org_id)
            .with_entities(
                OrgMapping.instance_org_id,
                OrgMapping.instance_org_name,
                OrgMapping.instance_org_acronym,
                OrgMapping.instance_org_type,
                OrgMapping.fund_name,
                OrgMapping.match_percent,
            )
            .limit(20)
            .all()
        )
        unique_organizations.append(
            {
                "global_org_id": go.global_org_id,
                "global_org_name": go.global_org_name,
                "global_org_acronym": go.global_acronym or "",
                "usage_count": go.usage_count or 0,
                "instance_organizations": [
                    {
                        "instance_org_id": row[0],
                        "instance_org_name": row[1],
                        "instance_org_acronym": row[2],
                        "instance_org_type": row[3],
                        "fund_name": row[4],
                        "match_percent": float(row[5]) if row[5] is not None else None,
                    }
                    for row in instance_orgs
                ],
            }
        )
    unique_organizations.sort(key=lambda x: -x["usage_count"])

    total_orgs = GlobalOrganization.query.count()
    return {
        "duplicate_groups": duplicate_groups,
        "unique_organizations": unique_organizations,
        "summary": {
            "total_organizations": total_orgs,
            "duplicate_groups_count": len(duplicate_groups),
            "unique_count": len(unique_organizations),
        },
    }
