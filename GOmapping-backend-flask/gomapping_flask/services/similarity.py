from collections import defaultdict
from difflib import SequenceMatcher

from sqlalchemy import func

from ..extensions import db
from ..knowledge_base import get_recommendation_score
from ..models import GlobalOrganization, GoSimilarity, OrgMapping


def _normalize(text: str) -> str:
    return " ".join((text or "").lower().split())


def compute_similarity_edges(threshold=70.0):
    gos = GlobalOrganization.query.order_by(GlobalOrganization.global_org_id.asc()).all()
    edges = []

    for i in range(len(gos)):
        a = gos[i]
        n1 = _normalize(a.global_org_name)
        for j in range(i + 1, len(gos)):
            b = gos[j]
            n2 = _normalize(b.global_org_name)
            if not n1 or not n2:
                continue
            score = round(SequenceMatcher(None, n1, n2).ratio() * 100, 2)
            if score >= threshold:
                edges.append((a.global_org_id, b.global_org_id, score))

    return edges


def recalculate_similarity_table(threshold=70.0):
    GoSimilarity.query.delete()
    edges = compute_similarity_edges(threshold=threshold)
    for source_id, target_id, score in edges:
        db.session.add(
            GoSimilarity(
                source_global_org_id=source_id,
                target_global_org_id=target_id,
                similarity_percent=score,
            )
        )
        db.session.add(
            GoSimilarity(
                source_global_org_id=target_id,
                target_global_org_id=source_id,
                similarity_percent=score,
            )
        )
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
