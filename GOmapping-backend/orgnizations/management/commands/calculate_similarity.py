"""
Django management command to calculate GO similarities and store in database.

This version is optimized for 3k~10k rows:
- Blocking (bucketing) to reduce candidate pairs drastically
- Batch INSERT (no per-row EXISTS checks)
- Optional: compute OrgMapping.match_percent / risk_level (GO vs instance org)

Usage:
  python manage.py calculate_similarity --clear
  python manage.py calculate_similarity --clear --threshold 60
  python manage.py calculate_similarity --clear --compute-mapping
"""

import re
import sys
import time
from difflib import SequenceMatcher
from html import unescape
from itertools import combinations

from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.utils import timezone

from orgnizations.models import GlobalOrganization, GoSimilarity, OrgMapping


STOP_WORDS = {
    # Only truly meaningless words (articles, prepositions, conjunctions)
    "the", "of", "for", "and", "in", "to", "a", "an", "at", "on", "&",
    "de", "del", "y", "et", "la", "le", "les", "el", "los", "las",
}


def normalize_name(name: str) -> str:
    if not name:
        return ""
    # Decode HTML entities like &#233; -> é
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


def weighted_similarity(norm1: str, tok1: set[str], acr1: str, norm2: str, tok2: set[str], acr2: str, 
                       original1: str = "", original2: str = "") -> float:
    if not norm1 or not norm2:
        return 0.0

    # Check if normalized names are identical
    if norm1 == norm2:
        # Also check if original names are very similar (to avoid false 100% matches)
        orig1_clean = original1.lower().strip() if original1 else norm1
        orig2_clean = original2.lower().strip() if original2 else norm2
        
        if orig1_clean == orig2_clean:
            return 100.0  # Truly identical
        else:
            # Normalized names match but originals differ slightly
            # Calculate similarity on original names to get more accurate score
            orig_sim = SequenceMatcher(None, orig1_clean, orig2_clean).ratio() * 100.0
            return min(orig_sim, 98.0)  # Cap at 98% to indicate they're not identical

    seq_sim = SequenceMatcher(None, norm1, norm2).ratio() * 100.0
    token_sim = jaccard(tok1, tok2) * 100.0
    acronym_sim = 100.0 if (acr1 and acr2 and acr1 == acr2) else 0.0

    if acronym_sim == 100.0:
        final_sim = 75.0 + (seq_sim * 0.15) + (token_sim * 0.10)
    else:
        final_sim = (seq_sim * 0.5) + (token_sim * 0.3) + (acronym_sim * 0.2)

    return min(final_sim, 100.0)


def risk_from_percent(p: float | None) -> str | None:
    if p is None:
        return None
    if p >= 85:
        return "LOW"
    if p >= 60:
        return "MEDIUM"
    return "HIGH"


def insert_go_similarity_rows(rows: list[tuple[int, int, float]], chunk_size: int = 500):
    if not rows:
        return
    with connection.cursor() as cursor:
        # SQL Server has a hard limit of 2100 parameters per statement.
        # Each row uses 3 params, so we must keep rows_per_stmt <= 700.
        rows_per_stmt = max(1, min(int(chunk_size), 700))
        for i in range(0, len(rows), rows_per_stmt):
            chunk = rows[i : i + rows_per_stmt]
            cursor.executemany(
                "INSERT INTO go_similarity (source_global_org_id, target_global_org_id, similarity_percent) VALUES (%s, %s, %s)",
                chunk,
            )


class _Progress:
    def __init__(self, label: str, total: int, min_interval_sec: float = 0.2):
        self.label = label
        self.total = max(int(total), 1)
        self.min_interval_sec = float(min_interval_sec)
        self.start = time.time()
        self.last = 0.0

    def update(self, current: int):
        now = time.time()
        if (now - self.last) < self.min_interval_sec and current < self.total:
            return
        self.last = now

        cur = min(int(current), self.total)
        pct = (cur / self.total) * 100.0
        elapsed = now - self.start
        rate = cur / elapsed if elapsed > 0 else 0.0
        remaining = (self.total - cur) / rate if rate > 0 else 0.0

        bar_len = 30
        filled = int((cur / self.total) * bar_len)
        bar = "=" * filled + "-" * (bar_len - filled)

        msg = (
            f"\r{self.label} [{bar}] {pct:6.2f}%  "
            f"{cur}/{self.total}  "
            f"elapsed {elapsed:6.1f}s  "
            f"eta {remaining:6.1f}s"
        )
        sys.stdout.write(msg)
        sys.stdout.flush()

    def done(self):
        self.update(self.total)
        sys.stdout.write("\n")
        sys.stdout.flush()


class Command(BaseCommand):
    help = "Fast similarity calculation using blocking + batch insert"

    def add_arguments(self, parser):
        parser.add_argument(
            "--threshold",
            type=float,
            default=70.0,
            help="Similarity threshold (default: 70.0)",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear go_similarity before calculation (recommended, fastest)",
        )
        parser.add_argument(
            "--max-bucket",
            type=int,
            default=250,
            help="Skip overly-large buckets to avoid explosion (default: 250)",
        )
        parser.add_argument(
            "--insert-chunk",
            type=int,
            default=1000,
            help="Insert chunk size for go_similarity (default: 1000)",
        )
        parser.add_argument(
            "--compute-mapping",
            action="store_true",
            help="Also compute OrgMapping.match_percent and risk_level (GO vs instance org name)",
        )

    def handle(self, *args, **options):
        threshold = float(options["threshold"])
        clear_existing = bool(options["clear"])
        max_bucket = int(options["max_bucket"])
        insert_chunk = int(options["insert_chunk"])
        compute_mapping = bool(options["compute_mapping"])

        self.stdout.write(self.style.SUCCESS("Fast GO similarity (blocking) starting..."))
        self.stdout.write(f"Threshold: {threshold}% | max_bucket: {max_bucket} | insert_chunk: {insert_chunk}")

        gos = list(GlobalOrganization.objects.values("global_org_id", "global_org_name", "global_acronym"))
        self.stdout.write("Preparing normalized fields...")
        p = _Progress("Normalize GOs", len(gos))
        for go in gos:
            norm = normalize_name(go.get("global_org_name") or "")
            go["norm"] = norm
            go["tok"] = token_set(norm)
            go["acr"] = (go.get("global_acronym") or "").upper().strip()
            p.update(p.total - (p.total - 1))  # keep linter happy (no-op)
        p.done()

        total_gos = len(gos)
        self.stdout.write(f"Total GOs: {total_gos}")

        # Buckets: key -> list[index]
        buckets: dict[str, list[int]] = {}
        p_bucket = _Progress("Build buckets", total_gos)
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

            # shortest informative token prefix
            if go["tok"]:
                shortest = min(go["tok"], key=len)
                if len(shortest) >= 4:
                    keys.add(f"sh:{shortest[:4]}")

            for k in keys:
                buckets.setdefault(k, []).append(idx)
            p_bucket.update(idx + 1)
        p_bucket.done()

        seen_pairs: set[tuple[int, int]] = set()
        candidate_pairs: list[tuple[int, int]] = []
        skipped_big = 0

        for _, idxs in buckets.items():
            if len(idxs) < 2:
                continue
            if len(idxs) > max_bucket:
                skipped_big += 1
                continue
            for a, b in combinations(idxs, 2):
                id1 = gos[a]["global_org_id"]
                id2 = gos[b]["global_org_id"]
                lo, hi = (id1, id2) if id1 < id2 else (id2, id1)
                k = (lo, hi)
                if k in seen_pairs:
                    continue
                seen_pairs.add(k)
                candidate_pairs.append((a, b))

        self.stdout.write(f"Buckets: {len(buckets)} | skipped_big_buckets: {skipped_big}")
        self.stdout.write(f"Candidate pairs: {len(candidate_pairs)} (naive would be {total_gos*(total_gos-1)//2})")

        edges: list[tuple[int, int, float]] = []
        checked = 0
        total_candidates = len(candidate_pairs)
        p_score = _Progress("Score candidates", max(total_candidates, 1))
        for a, b in candidate_pairs:
            checked += 1
            if checked % 2000 == 0 or checked == total_candidates:
                p_score.update(checked)

            go1 = gos[a]
            go2 = gos[b]

            jac = jaccard(go1["tok"], go2["tok"])
            if jac < 0.10 and not (go1["acr"] and go2["acr"] and go1["acr"] == go2["acr"]):
                continue

            sim = weighted_similarity(
                go1["norm"], go1["tok"], go1["acr"], 
                go2["norm"], go2["tok"], go2["acr"],
                go1.get("global_org_name", ""), go2.get("global_org_name", "")
            )
            if sim >= threshold:
                edges.append((go1["global_org_id"], go2["global_org_id"], round(sim, 2)))
        p_score.done()

        self.stdout.write(self.style.SUCCESS(f"Edges found (undirected): {len(edges)}"))

        to_insert: list[tuple[int, int, float]] = []
        for (id1, id2, sim) in edges:
            to_insert.append((id1, id2, sim))
            to_insert.append((id2, id1, sim))

        self.stdout.write(f"Inserting rows into go_similarity: {len(to_insert)}")
        with transaction.atomic():
            if clear_existing:
                self.stdout.write("Clearing go_similarity ...")
                with connection.cursor() as cursor:
                    cursor.execute("DELETE FROM go_similarity")
                self.stdout.write(self.style.SUCCESS("go_similarity cleared."))

            self._insert_similarity_rows_with_progress(
                to_insert,
                chunk_size=max(100, min(insert_chunk, 2000)),
            )

        self.stdout.write(self.style.SUCCESS("go_similarity done."))

        if compute_mapping:
            self.stdout.write(self.style.SUCCESS("Computing OrgMapping match_percent/risk_level ..."))
            self._compute_mapping_similarity(gos)
            self.stdout.write(self.style.SUCCESS("OrgMapping match_percent/risk_level done."))

    def _compute_mapping_similarity(self, gos):
        # Store original name along with normalized data
        go_info = {
            go["global_org_id"]: (go["norm"], go["tok"], go["acr"], go.get("global_org_name", "")) 
            for go in gos
        }

        qs = OrgMapping.objects.values("id", "global_org_id", "instance_org_name", "instance_org_acronym")

        updates = []
        now = timezone.now()
        count = 0
        total_rows = OrgMapping.objects.count()
        p_map = _Progress("Compute mapping match%", max(total_rows, 1))
        for row in qs.iterator(chunk_size=2000):
            count += 1
            if count % 500 == 0 or count == total_rows:
                p_map.update(count)

            go_norm, go_tok, go_acr, go_original = go_info.get(row["global_org_id"], ("", set(), "", ""))

            inst_name = row.get("instance_org_name") or ""
            inst_norm = normalize_name(inst_name)
            inst_tok = token_set(inst_norm)
            inst_acr = (row.get("instance_org_acronym") or "").upper().strip()

            sim = weighted_similarity(
                go_norm, go_tok, go_acr, 
                inst_norm, inst_tok, inst_acr,
                go_original, inst_name
            )
            sim = round(sim, 2)

            updates.append(
                OrgMapping(
                    id=row["id"],
                    match_percent=sim,
                    risk_level=risk_from_percent(sim),
                    updated_at=now,
                )
            )

            if len(updates) >= 2000:
                OrgMapping.objects.bulk_update(updates, ["match_percent", "risk_level", "updated_at"], batch_size=2000)
                updates = []

        if updates:
            OrgMapping.objects.bulk_update(updates, ["match_percent", "risk_level", "updated_at"], batch_size=2000)
        p_map.done()

    def _insert_similarity_rows_with_progress(self, rows: list[tuple[int, int, float]], chunk_size: int = 1000):
        if not rows:
            return
        total = len(rows)
        p_ins = _Progress("Insert go_similarity", max(total, 1))
        inserted = 0

        with connection.cursor() as cursor:
            # SQL Server param limit: 2100 params/statement => 700 rows max here.
            rows_per_stmt = max(1, min(int(chunk_size), 700))
            for i in range(0, total, rows_per_stmt):
                chunk = rows[i : i + rows_per_stmt]
                cursor.executemany(
                    "INSERT INTO go_similarity (source_global_org_id, target_global_org_id, similarity_percent) VALUES (%s, %s, %s)",
                    chunk,
                )
                inserted += len(chunk)
                p_ins.update(inserted)
        p_ins.done()

