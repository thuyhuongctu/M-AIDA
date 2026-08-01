#!/usr/bin/env python3
"""Create a deterministic, stratified candidate sample for M-AIDA validation."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


SOURCE_REQUIRED = {
    "study_id", "effect_id", "icrv", "cdai", "dpl", "n",
    "doi_type", "fp_type",
}
OUTPUT_FIELDS = [
    "selection_group", "sample_order", "study_id", "label", "year", "dpl",
    "icrv", "cdai", "doi_type", "fp_type", "effect_count", "min_n", "max_n",
    "full_text_status", "development_use", "coder1_status", "coder2_status",
    "adjudication_status", "route_coverage", "notes",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def selection_fingerprint(rows: list[dict[str, Any]]) -> str:
    payload = "\n".join(
        f"{row['selection_group']}|{row['sample_order']}|{row['study_id']}"
        for row in rows
    ) + "\n"
    return hashlib.sha256(payload.encode()).hexdigest()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = sorted(SOURCE_REQUIRED - set(reader.fieldnames or []))
        if missing:
            raise ValueError(f"{path}: missing columns: {', '.join(missing)}")
        rows = list(reader)
    if not rows:
        raise ValueError(f"{path}: no rows")
    return rows


def demo_study_ids(path: Path) -> set[str]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if "study_id" not in (reader.fieldnames or []):
            raise ValueError(f"{path}: missing study_id")
        return {row["study_id"].strip() for row in reader if row["study_id"].strip()}


def parse_year(label: str) -> int:
    years = re.findall(r"(?:19|20)\d{2}", label)
    if not years:
        raise ValueError(f"cannot parse publication year from label: {label}")
    return int(years[-1])


def collapse(rows: list[dict[str, str]], excluded: set[str]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        study_id = row["study_id"].strip()
        if not study_id:
            raise ValueError("source contains blank study_id")
        grouped[study_id].append(row)

    studies = []
    for study_id, effects in grouped.items():
        if study_id in excluded:
            continue
        labels = {
            (row.get("label") or f"{row.get('author', '')} {row.get('year', '')}").strip()
            for row in effects
        }
        dpls = {row["dpl"].strip() for row in effects}
        icrvs = {row["icrv"].strip() for row in effects}
        if len(labels) != 1 or len(dpls) != 1 or len(icrvs) != 1:
            raise ValueError(f"{study_id}: inconsistent label/dpl/icrv across effects")
        sample_sizes = [int(float(row["n"])) for row in effects]
        studies.append({
            "study_id": study_id,
            "label": next(iter(labels)),
            "year": parse_year(next(iter(labels))),
            "dpl": next(iter(dpls)),
            "icrv": next(iter(icrvs)),
            "cdai": "|".join(sorted({row["cdai"].strip() for row in effects})),
            "doi_type": "|".join(sorted({row["doi_type"].strip() for row in effects})),
            "fp_type": "|".join(sorted({row["fp_type"].strip() for row in effects})),
            "effect_count": len(effects),
            "min_n": min(sample_sizes),
            "max_n": max(sample_sizes),
            "stratum": f"{next(iter(dpls))}|{next(iter(icrvs))}",
        })
    return studies


def stable_rank(seed: str, study_id: str) -> str:
    return hashlib.sha256(f"{seed}|{study_id}".encode()).hexdigest()


def allocate(pool: list[dict[str, Any]], count: int, *, cover_all: bool = True) -> dict[str, int]:
    sizes = Counter(row["stratum"] for row in pool)
    if cover_all and count < len(sizes):
        raise ValueError(f"sample size {count} cannot cover {len(sizes)} non-empty strata")
    if count > len(pool):
        raise ValueError(f"requested {count} records from a pool of {len(pool)}")

    quotas = {stratum: (1 if cover_all else 0) for stratum in sizes}
    remaining = count - sum(quotas.values())
    capacity = {stratum: sizes[stratum] - 1 for stratum in sizes}
    total_capacity = sum(capacity.values())
    ideals = {
        stratum: (remaining * capacity[stratum] / total_capacity if total_capacity else 0)
        for stratum in sizes
    }
    for stratum in sizes:
        addition = min(capacity[stratum], int(ideals[stratum]))
        quotas[stratum] += addition
        remaining -= addition
    order = sorted(
        sizes,
        key=lambda stratum: (ideals[stratum] - int(ideals[stratum]), capacity[stratum], stratum),
        reverse=True,
    )
    while remaining:
        progressed = False
        for stratum in order:
            if quotas[stratum] < sizes[stratum]:
                quotas[stratum] += 1
                remaining -= 1
                progressed = True
                if not remaining:
                    break
        if not progressed:
            raise ValueError("unable to allocate all sample slots")
    return quotas


def stratified_select(
    pool: list[dict[str, Any]], count: int, seed: str, *, cover_all: bool = True,
) -> list[dict[str, Any]]:
    quotas = allocate(pool, count, cover_all=cover_all)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in pool:
        grouped[row["stratum"]].append(row)
    selected = []
    for stratum, rows in sorted(grouped.items()):
        ranked = sorted(rows, key=lambda row: stable_rank(seed, row["study_id"]))
        selected.extend(ranked[:quotas[stratum]])
    return sorted(selected, key=lambda row: stable_rank(f"{seed}|order", row["study_id"]))


def build_candidate(
    source_rows: list[dict[str, str]], excluded: set[str], primary_count: int,
    reserve_count: int, seed: str,
) -> list[dict[str, Any]]:
    studies = collapse(source_rows, excluded)
    primary = stratified_select(studies, primary_count, f"{seed}|primary")
    primary_ids = {row["study_id"] for row in primary}
    remaining = [row for row in studies if row["study_id"] not in primary_ids]
    reserve = stratified_select(
        remaining, reserve_count, f"{seed}|reserve", cover_all=False,
    )

    output = []
    for group, rows in (("PRIMARY", primary), ("RESERVE", reserve)):
        for order, row in enumerate(rows, 1):
            output.append({
                **{key: row[key] for key in OUTPUT_FIELDS if key in row},
                "selection_group": group,
                "sample_order": order,
                "full_text_status": "TO_CONFIRM",
                "development_use": "TO_CONFIRM",
                "coder1_status": "NOT_STARTED",
                "coder2_status": "NOT_STARTED",
                "adjudication_status": "NOT_STARTED",
                "route_coverage": "TO_CODE",
                "notes": "",
            })
    return output


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--demo-seed", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--metadata-out", type=Path, required=True)
    parser.add_argument("--seed", required=True)
    parser.add_argument("--primary", type=int, default=40)
    parser.add_argument("--reserve", type=int, default=10)
    parser.add_argument("--source-repository", required=True)
    parser.add_argument("--source-ref", required=True)
    parser.add_argument("--source-path", required=True)
    parser.add_argument("--source-blob-sha", required=True)
    args = parser.parse_args()

    source_rows = read_rows(args.source)
    demo_excluded = demo_study_ids(args.demo_seed)
    estimated_excluded = {
        row["study_id"].strip()
        for row in source_rows
        if row.get("is_estimated", "0").strip() not in {"", "0"}
    }
    excluded = demo_excluded | estimated_excluded
    rows = build_candidate(source_rows, excluded, args.primary, args.reserve, args.seed)
    write_csv(args.output, rows)
    metadata = {
        "status": "PROVISIONAL",
        "reason_not_locked": [
            "full_text availability is not yet confirmed for every PRIMARY study",
            "non-use in M-AIDA development/prompt tuning is not yet confirmed",
        ],
        "seed": args.seed,
        "primary_count": args.primary,
        "reserve_count": args.reserve,
        "excluded_demo_study_ids": sorted(demo_excluded),
        "excluded_estimated_study_ids": sorted(estimated_excluded),
        "source": {
            "repository": args.source_repository,
            "ref": args.source_ref,
            "path": args.source_path,
            "git_blob_sha": args.source_blob_sha,
            "normalized_file_sha256": sha256_file(args.source),
        },
        "candidate_manifest_sha256": sha256_file(args.output),
        "selection_fingerprint_sha256": selection_fingerprint(rows),
        "strata": dict(sorted(Counter(f"{row['dpl']}|{row['icrv']}" for row in rows if row["selection_group"] == "PRIMARY").items())),
        "scope": "global published I–P literature; Asian institutional interpretation where relevant",
        "osf": {"code": "Z37KN", "doi": "10.17605/OSF.IO/Z37KN"},
    }
    args.metadata_out.parent.mkdir(parents=True, exist_ok=True)
    args.metadata_out.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
