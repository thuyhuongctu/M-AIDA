#!/usr/bin/env python3
"""Turn one frozen benchmark run into predictions.csv for analyze_validation.py.

Inputs (all files are read, never modified):

    --gold        the adjudicated, locked gold standard (gold_standard.csv)
    --run         a run directory written by run_benchmark.py, holding
                  run_manifest.json, proposals.csv and the two files the
                  people fill in after the run:
                    proposal_matches.csv   which gold case_id each machine
                                           proposal corresponds to
                    verification_log.csv   the PI's assisted-verification time
                                           and decisions, one row per paper

Rules, fixed before any result is seen:

* M-AIDA proposes at most one effect per paper. The case it was matched to is
  predicted in scope with the untouched machine values; every other case of
  that paper is predicted out of scope. A paper whose extraction was rejected
  by the evidence gate, or whose proposal carries no r, has no proposal: all
  of its cases are predicted out of scope.
* Every proposal must be resolved as MATCHED to a gold case of the same paper.
  NOT_IN_FRAME (a real coefficient the enumeration missed) and HALLUCINATED
  (values that are not in the paper) are not silently dropped: the
  adjudicators first add a gold row for that coefficient (adjudication_notes
  starting with ADDED_AFTER_RUN), then re-mark the proposal MATCHED. The
  script reports how many such rows exist.
* The paper's verification minutes go on the matched case (or, for a paper
  without a proposal, on its first case); the other cases get 0, so means over
  cases compare the same paper totals as the manual coding minutes.
* REHEARSAL runs and runs with failed (provider/internal) extractions are
  refused; resume the run until every paper is succeeded or rejected.

    python validation/build_predictions.py --gold validation/gold_standard.csv \\
        --run validation/runs/2026-10-xx --out validation/runs/2026-10-xx/predictions.csv
    python validation/analyze_validation.py --gold validation/gold_standard.csv \\
        --predictions validation/runs/2026-10-xx/predictions.csv \\
        --json-out validation/results/validation_metrics.json --markdown-out validation/results/VALIDATION_REPORT.md
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

PRED_COLUMNS = [
    "case_id", "predicted_in_scope", "predicted_route", "predicted_r", "predicted_n",
    "predicted_doi_measure", "predicted_performance_measure", "confidence", "requires_verification",
    "fields_corrected", "verification_minutes", "hallucinated", "provenance_present",
    "model_provider", "model_id", "prompt_version", "temperature", "run_date", "verifier_id",
]
MATCH_STATUSES = {"MATCHED", "NOT_IN_FRAME", "HALLUCINATED"}
ADDED_MARK = "ADDED_AFTER_RUN"


def read(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise SystemExit(f"missing input: {path}")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(handle)]


def truthy(value: str, where: str) -> bool:
    text = value.strip().lower()
    if text in ("true", "1", "yes", "y"):
        return True
    if text in ("false", "0", "no", "n"):
        return False
    raise SystemExit(f"{where}: expected TRUE or FALSE, got {value!r}")


def number(value: str, where: str) -> float:
    try:
        result = float(value)
    except ValueError:
        raise SystemExit(f"{where}: expected a number, got {value!r}") from None
    if not math.isfinite(result) or result < 0:
        raise SystemExit(f"{where}: expected a non-negative number, got {value!r}")
    return result


def build(gold_path: Path, run_dir: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    manifest_path = run_dir / "run_manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"{manifest_path} is missing: the run did not finish")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("kind") != "VALIDATION_RUN":
        raise SystemExit(f"{run_dir} is a {manifest.get('kind')} run; predictions are built only from a VALIDATION_RUN")
    temperature = manifest.get("temperature")
    if not isinstance(temperature, (int, float)):
        raise SystemExit("the run manifest has no numeric temperature: the configuration was not frozen")
    provenance = {
        "model_provider": manifest.get("model_provider") or "",
        "model_id": manifest.get("model_identifier") or "",
        "prompt_version": manifest.get("prompt_version") or "",
        "temperature": temperature,
        "run_date": manifest.get("extraction_date") or "",
    }
    if not all(str(v) for v in provenance.values()):
        raise SystemExit(f"the run manifest lacks provenance fields: {provenance}")

    gold = read(gold_path)
    cases_by_paper: dict[str, list[dict[str, str]]] = defaultdict(list)
    case_ids = set()
    for g in gold:
        cases_by_paper[g["paper_id"]].append(g)
        case_ids.add(g["case_id"])
    proposals = {p["paper_id"]: p for p in read(run_dir / "proposals.csv")}
    problems: list[str] = []
    for pid in sorted(set(cases_by_paper) - set(proposals)):
        problems.append(f"{pid}: in the gold standard but not in this run")
    for pid in sorted(set(proposals) - set(cases_by_paper)):
        problems.append(f"{pid}: in this run but not in the gold standard")
    failed = sorted(pid for pid, p in proposals.items() if p["outcome"] not in ("succeeded", "rejected"))
    if failed:
        problems.append("failed extractions (resume the run first): " + ", ".join(failed))

    usable = {pid for pid, p in proposals.items() if p["outcome"] == "succeeded" and p["effect_r"] != ""}
    matches: dict[str, str] = {}
    for m in read(run_dir / "proposal_matches.csv"):
        pid, status, target = m["paper_id"], m["match_status"].upper(), m["matched_case_id"]
        if pid not in usable:
            problems.append(f"{pid}: proposal_matches.csv has a row but the run has no usable proposal for it")
            continue
        if pid in matches:
            problems.append(f"{pid}: more than one match row")
            continue
        if status not in MATCH_STATUSES:
            problems.append(f"{pid}: match_status must be one of {sorted(MATCH_STATUSES)} (got {status or 'blank'})")
        elif status != "MATCHED":
            problems.append(f"{pid}: {status}; add the coefficient to the gold standard ({ADDED_MARK}) and mark it MATCHED")
        elif target not in case_ids:
            problems.append(f"{pid}: matched_case_id {target or '(blank)'} is not in the gold standard")
        elif not any(c["case_id"] == target for c in cases_by_paper[pid]):
            problems.append(f"{pid}: matched_case_id {target} belongs to another paper")
        else:
            matches[pid] = target
    for pid in sorted(usable - set(matches)):
        if not any(p.startswith(f"{pid}:") for p in problems):
            problems.append(f"{pid}: the machine proposal has not been matched (proposal_matches.csv)")

    log = {}
    for v in read(run_dir / "verification_log.csv"):
        log[v["paper_id"]] = v
    for pid in sorted(proposals):
        v = log.get(pid)
        if v is None or not v.get("verifier_id") or v.get("verification_minutes", "") == "":
            problems.append(f"{pid}: verification_log.csv needs verifier_id and verification_minutes")
        elif pid in usable and (v.get("fields_corrected", "") == "" or v.get("hallucinated", "") == ""):
            problems.append(f"{pid}: verification_log.csv needs fields_corrected and hallucinated for a proposal")
    if problems:
        raise SystemExit("predictions not built:\n- " + "\n- ".join(problems))

    rows: list[dict[str, Any]] = []
    for pid in sorted(cases_by_paper):
        p, v = proposals[pid], log[pid]
        minutes = number(v["verification_minutes"], f"{pid} verification_minutes")
        target = matches.get(pid) or cases_by_paper[pid][0]["case_id"]
        for case in cases_by_paper[pid]:
            row: dict[str, Any] = {c: "" for c in PRED_COLUMNS}
            row.update(provenance)
            row.update(case_id=case["case_id"], verifier_id=v["verifier_id"],
                       verification_minutes=minutes if case["case_id"] == target else 0,
                       predicted_in_scope="FALSE", fields_corrected=0, hallucinated="FALSE",
                       provenance_present="FALSE", requires_verification="")
            if matches.get(pid) == case["case_id"]:
                corrected = number(v["fields_corrected"], f"{pid} fields_corrected")
                if not corrected.is_integer():
                    raise SystemExit(f"{pid}: fields_corrected must be a whole number")
                row.update(
                    predicted_in_scope="TRUE", predicted_route=p["predicted_route"], predicted_r=p["effect_r"],
                    predicted_n=p["sample_n"], predicted_doi_measure=p["doi_measure"],
                    predicted_performance_measure=p["performance_measure"], confidence=p["extraction_confidence"],
                    requires_verification=p["requires_verification"], fields_corrected=int(corrected),
                    hallucinated="TRUE" if truthy(v["hallucinated"], f"{pid} hallucinated") else "FALSE",
                    provenance_present=p["provenance_present"],
                )
            rows.append(row)

    added = sum(g.get("adjudication_notes", "").startswith(ADDED_MARK) for g in gold)
    summary = {
        "papers": len(cases_by_paper), "cases": len(rows),
        "outcomes": dict(Counter(p["outcome"] for p in proposals.values())),
        "proposals_matched": len(matches),
        "papers_without_proposal": len(cases_by_paper) - len(matches),
        "gold_rows_added_after_run": added,
        **provenance,
    }
    return rows, summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--gold", type=Path, required=True)
    ap.add_argument("--run", type=Path, required=True, help="run directory written by run_benchmark.py")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    if args.out.exists():
        raise SystemExit(f"{args.out} exists; outputs are never overwritten")
    rows, summary = build(args.gold, args.run)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=PRED_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
