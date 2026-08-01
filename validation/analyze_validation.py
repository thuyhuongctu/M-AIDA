#!/usr/bin/env python3
"""Analyze an independently coded M-AIDA validation benchmark.

The program uses only the Python standard library so the frozen benchmark can
be rerun without the application or an LLM provider. It evaluates untouched
machine proposals against an adjudicated human gold standard; it does not run
the meta-analysis or interpret dissertation results.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import fmean
from typing import Any, Iterable


GOLD_REQUIRED = {
    "case_id",
    "paper_id",
    "effect_id",
    "source_locator",
    "coder1_in_scope",
    "coder2_in_scope",
    "gold_in_scope",
    "coder1_route",
    "coder2_route",
    "gold_route",
    "gold_r",
    "gold_n",
    "gold_doi_measure",
    "gold_performance_measure",
    "manual_minutes",
    "adjudication_notes",
}
PRED_REQUIRED = {
    "case_id",
    "predicted_in_scope",
    "predicted_route",
    "predicted_r",
    "predicted_n",
    "predicted_doi_measure",
    "predicted_performance_measure",
    "confidence",
    "requires_verification",
    "fields_corrected",
    "verification_minutes",
    "hallucinated",
    "provenance_present",
    "model_provider",
    "model_id",
    "prompt_version",
    "temperature",
    "run_date",
    "verifier_id",
}
TRUE_VALUES = {"1", "true", "yes", "y"}
FALSE_VALUES = {"0", "false", "no", "n"}


def read_csv(path: Path, required: set[str]) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or [])
        missing = sorted(required - columns)
        if missing:
            raise ValueError(f"{path}: missing columns: {', '.join(missing)}")
        rows = list(reader)
    if not rows:
        raise ValueError(f"{path}: no data rows")
    identifiers = [row["case_id"].strip() for row in rows]
    if any(not value for value in identifiers):
        raise ValueError(f"{path}: case_id must not be blank")
    duplicates = sorted(key for key, count in Counter(identifiers).items() if count > 1)
    if duplicates:
        raise ValueError(f"{path}: duplicate case_id: {', '.join(duplicates)}")
    return rows


def as_bool(value: str, field: str, case_id: str) -> bool:
    normalized = value.strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    raise ValueError(f"{case_id}: {field} must be TRUE or FALSE")


def as_float(value: str, field: str, case_id: str, *, optional: bool = False) -> float | None:
    if optional and not value.strip():
        return None
    try:
        result = float(value)
    except ValueError as exc:
        raise ValueError(f"{case_id}: {field} must be numeric") from exc
    if not math.isfinite(result):
        raise ValueError(f"{case_id}: {field} must be finite")
    return result


def as_int(value: str, field: str, case_id: str, *, optional: bool = False) -> int | None:
    number = as_float(value, field, case_id, optional=optional)
    if number is None:
        return None
    if not number.is_integer():
        raise ValueError(f"{case_id}: {field} must be an integer")
    return int(number)


def safe_div(numerator: float, denominator: float) -> float | None:
    return numerator / denominator if denominator else None


def wilson(successes: int, total: int) -> list[float] | None:
    if total == 0:
        return None
    z = 1.959963984540054
    proportion = successes / total
    denominator = 1 + z * z / total
    centre = (proportion + z * z / (2 * total)) / denominator
    half = z * math.sqrt(
        proportion * (1 - proportion) / total + z * z / (4 * total * total)
    ) / denominator
    return [max(0.0, centre - half), min(1.0, centre + half)]


def proportion(successes: int, total: int) -> dict[str, Any]:
    return {"value": safe_div(successes, total), "numerator": successes, "n": total, "ci95": wilson(successes, total)}


def cohen_kappa(left: Iterable[str], right: Iterable[str]) -> float | None:
    pairs = list(zip(left, right))
    if not pairs:
        return None
    observed = sum(a == b for a, b in pairs) / len(pairs)
    left_counts = Counter(a for a, _ in pairs)
    right_counts = Counter(b for _, b in pairs)
    expected = sum(
        left_counts[label] * right_counts[label] for label in left_counts | right_counts
    ) / (len(pairs) ** 2)
    if math.isclose(expected, 1.0):
        return 1.0 if math.isclose(observed, 1.0) else None
    return (observed - expected) / (1 - expected)


def same_sign(left: float, right: float) -> bool:
    return (left > 0) == (right > 0) and (left < 0) == (right < 0)


def analyze(gold_rows: list[dict[str, str]], pred_rows: list[dict[str, str]], tolerance: float) -> dict[str, Any]:
    gold = {row["case_id"].strip(): row for row in gold_rows}
    predictions = {row["case_id"].strip(): row for row in pred_rows}
    missing = sorted(gold.keys() - predictions.keys())
    unexpected = sorted(predictions.keys() - gold.keys())
    if missing or unexpected:
        details = []
        if missing:
            details.append(f"missing predictions: {', '.join(missing)}")
        if unexpected:
            details.append(f"unexpected predictions: {', '.join(unexpected)}")
        raise ValueError("; ".join(details))

    tp = fp = fn = tn = 0
    exact_r = correct_sign = exact_n = exact_route = 0
    exact_doi_measure = exact_performance_measure = 0
    errors: list[float] = []
    matched = 0
    predicted_positive = 0
    corrected = hallucinated = provenance = 0
    manual_times: list[float] = []
    verification_times: list[float] = []
    confidence_groups: dict[str, list[bool]] = defaultdict(list)
    route_groups: dict[str, dict[str, Any]] = defaultdict(lambda: {"n": 0, "exact_r": 0, "errors": []})
    run_configurations: set[tuple[str, str, str, float, str]] = set()
    verifiers: set[str] = set()

    coder1_scope: list[str] = []
    coder2_scope: list[str] = []
    coder1_routes: list[str] = []
    coder2_routes: list[str] = []

    for case_id in sorted(gold):
        g = gold[case_id]
        p = predictions[case_id]
        g_scope = as_bool(g["gold_in_scope"], "gold_in_scope", case_id)
        p_scope = as_bool(p["predicted_in_scope"], "predicted_in_scope", case_id)
        provider = p["model_provider"].strip()
        model_id = p["model_id"].strip()
        prompt_version = p["prompt_version"].strip()
        run_date = p["run_date"].strip()
        verifier = p["verifier_id"].strip()
        if not all((provider, model_id, prompt_version, run_date, verifier)):
            raise ValueError(f"{case_id}: run provenance fields must not be blank")
        temperature = as_float(p["temperature"], "temperature", case_id)
        run_configurations.add((provider, model_id, prompt_version, float(temperature), run_date))
        verifiers.add(verifier)
        coder1_scope.append(str(as_bool(g["coder1_in_scope"], "coder1_in_scope", case_id)))
        coder2_scope.append(str(as_bool(g["coder2_in_scope"], "coder2_in_scope", case_id)))

        if g["coder1_route"].strip() and g["coder2_route"].strip():
            coder1_routes.append(g["coder1_route"].strip())
            coder2_routes.append(g["coder2_route"].strip())

        manual = as_float(g["manual_minutes"], "manual_minutes", case_id)
        verify = as_float(p["verification_minutes"], "verification_minutes", case_id)
        if manual is not None and manual < 0 or verify is not None and verify < 0:
            raise ValueError(f"{case_id}: time values must be non-negative")
        manual_times.append(float(manual))
        verification_times.append(float(verify))

        if g_scope and p_scope:
            tp += 1
        elif not g_scope and p_scope:
            fp += 1
        elif g_scope and not p_scope:
            fn += 1
        else:
            tn += 1

        if p_scope:
            predicted_positive += 1
            correction_count = as_int(p["fields_corrected"], "fields_corrected", case_id)
            if correction_count < 0:
                raise ValueError(f"{case_id}: fields_corrected must be non-negative")
            corrected += correction_count > 0
            hallucinated += as_bool(p["hallucinated"], "hallucinated", case_id)
            provenance += as_bool(p["provenance_present"], "provenance_present", case_id)

        if not (g_scope and p_scope):
            continue

        matched += 1
        gold_r = as_float(g["gold_r"], "gold_r", case_id)
        predicted_r = as_float(p["predicted_r"], "predicted_r", case_id)
        if abs(float(gold_r)) > 1 or abs(float(predicted_r)) > 1:
            raise ValueError(f"{case_id}: correlations must be within [-1, 1]")
        error = abs(float(gold_r) - float(predicted_r))
        is_exact = error <= tolerance
        exact_r += is_exact
        correct_sign += same_sign(float(gold_r), float(predicted_r))
        errors.append(error)

        gold_n = as_int(g["gold_n"], "gold_n", case_id)
        pred_n = as_int(p["predicted_n"], "predicted_n", case_id)
        if gold_n <= 0 or pred_n <= 0:
            raise ValueError(f"{case_id}: sample sizes must be positive")
        exact_n += gold_n == pred_n

        gold_route = g["gold_route"].strip()
        exact_route += gold_route == p["predicted_route"].strip()
        exact_doi_measure += g["gold_doi_measure"].strip() == p["predicted_doi_measure"].strip()
        exact_performance_measure += (
            g["gold_performance_measure"].strip()
            == p["predicted_performance_measure"].strip()
        )
        route_groups[gold_route]["n"] += 1
        route_groups[gold_route]["exact_r"] += is_exact
        route_groups[gold_route]["errors"].append(error)

        confidence = as_float(p["confidence"], "confidence", case_id)
        if not 0 <= float(confidence) <= 1:
            raise ValueError(f"{case_id}: confidence must be within [0, 1]")
        confidence_groups[f"{float(confidence):.1f}"].append(is_exact)

    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, tp + fn)
    f1 = safe_div(2 * precision * recall, precision + recall) if precision is not None and recall is not None else None
    manual_mean = fmean(manual_times)
    verification_mean = fmean(verification_times)
    if len(run_configurations) != 1:
        raise ValueError("predictions must use one frozen provider/model/prompt/temperature/date configuration")
    provider, model_id, prompt_version, temperature, run_date = next(iter(run_configurations))

    return {
        "status": "observed benchmark results; interpret only with the archived input files",
        "run_configuration": {
            "model_provider": provider,
            "model_id": model_id,
            "prompt_version": prompt_version,
            "temperature": temperature,
            "run_date": run_date,
            "verifier_ids": sorted(verifiers),
        },
        "sample": {"cases": len(gold), "gold_positive": tp + fn, "predicted_positive": tp + fp},
        "selection": {
            "confusion_matrix": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
            "precision": precision,
            "recall": recall,
            "f1": f1,
        },
        "field_accuracy": {
            "r_exact": proportion(exact_r, matched),
            "sign": proportion(correct_sign, matched),
            "sample_n_exact": proportion(exact_n, matched),
            "route_exact": proportion(exact_route, matched),
            "doi_measure_exact": proportion(exact_doi_measure, matched),
            "performance_measure_exact": proportion(exact_performance_measure, matched),
            "r_mae": fmean(errors) if errors else None,
            "r_rmse": math.sqrt(fmean(error * error for error in errors)) if errors else None,
            "r_tolerance": tolerance,
        },
        "governance": {
            "machine_proposal_correction_rate": proportion(corrected, predicted_positive),
            "machine_proposal_hallucination_rate": proportion(hallucinated, predicted_positive),
            "proposal_provenance_completeness": proportion(provenance, predicted_positive),
        },
        "time": {
            "manual_minutes_mean": manual_mean,
            "assisted_verification_minutes_mean": verification_mean,
            "time_saving_fraction": safe_div(manual_mean - verification_mean, manual_mean),
            "paired_cases": len(manual_times),
        },
        "human_coder_agreement": {
            "in_scope_cohen_kappa": cohen_kappa(coder1_scope, coder2_scope),
            "route_cohen_kappa": cohen_kappa(coder1_routes, coder2_routes),
            "route_pairs": len(coder1_routes),
        },
        "by_gold_route": {
            route: {
                "n": values["n"],
                "r_exact": proportion(values["exact_r"], values["n"]),
                "r_mae": fmean(values["errors"]),
            }
            for route, values in sorted(route_groups.items())
        },
        "exact_r_by_confidence": {
            confidence: proportion(sum(matches), len(matches))
            for confidence, matches in sorted(confidence_groups.items())
        },
    }


def display(value: Any, digits: int = 3) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def markdown_report(metrics: dict[str, Any]) -> str:
    selection = metrics["selection"]
    fields = metrics["field_accuracy"]
    governance = metrics["governance"]
    timing = metrics["time"]
    agreement = metrics["human_coder_agreement"]
    lines = [
        "# M-AIDA independent validation report",
        "",
        "> This report contains observed benchmark results generated from the archived",
        "> gold-standard and prediction files. Software-test fixtures are not evidence.",
        "",
        "## Sample and focal-effect selection",
        "",
        f"- Cases: {metrics['sample']['cases']}",
        f"- Gold-standard positive cases: {metrics['sample']['gold_positive']}",
        f"- Precision / Recall / F1: {display(selection['precision'])} / {display(selection['recall'])} / {display(selection['f1'])}",
        f"- Confusion matrix (TP / FP / FN / TN): {selection['confusion_matrix']['tp']} / {selection['confusion_matrix']['fp']} / {selection['confusion_matrix']['fn']} / {selection['confusion_matrix']['tn']}",
        "",
        "## Extraction accuracy",
        "",
        "| Metric | Result | N |",
        "|---|---:|---:|",
        f"| Exact r (tolerance {fields['r_tolerance']}) | {display(fields['r_exact']['value'])} | {fields['r_exact']['n']} |",
        f"| Correct sign | {display(fields['sign']['value'])} | {fields['sign']['n']} |",
        f"| Exact sample N | {display(fields['sample_n_exact']['value'])} | {fields['sample_n_exact']['n']} |",
        f"| Correct conversion route | {display(fields['route_exact']['value'])} | {fields['route_exact']['n']} |",
        f"| Exact DOI measure class | {display(fields['doi_measure_exact']['value'])} | {fields['doi_measure_exact']['n']} |",
        f"| Exact performance class | {display(fields['performance_measure_exact']['value'])} | {fields['performance_measure_exact']['n']} |",
        f"| r MAE | {display(fields['r_mae'], 4)} | {fields['r_exact']['n']} |",
        f"| r RMSE | {display(fields['r_rmse'], 4)} | {fields['r_exact']['n']} |",
        "",
        "## Governance and timing",
        "",
        f"- Machine-proposal correction rate: {display(governance['machine_proposal_correction_rate']['value'])}",
        f"- Machine-proposal hallucination rate: {display(governance['machine_proposal_hallucination_rate']['value'])}",
        f"- Proposal provenance completeness: {display(governance['proposal_provenance_completeness']['value'])}",
        f"- Mean manual / assisted-verification minutes: {display(timing['manual_minutes_mean'], 2)} / {display(timing['assisted_verification_minutes_mean'], 2)}",
        f"- Paired time saving: {display(timing['time_saving_fraction'])}",
        f"- Human coder kappa (scope / route): {display(agreement['in_scope_cohen_kappa'])} / {display(agreement['route_cohen_kappa'])}",
        "",
        "## Accuracy by gold-standard conversion route",
        "",
        "| Route | N | Exact r | r MAE |",
        "|---|---:|---:|---:|",
    ]
    for route, values in metrics["by_gold_route"].items():
        lines.append(f"| {route} | {values['n']} | {display(values['r_exact']['value'])} | {display(values['r_mae'], 4)} |")
    lines.extend([
        "",
        "## Interpretation boundary",
        "",
        "These metrics assess effect-size data preparation. They do not validate study",
        "eligibility decisions, risk-of-bias assessment, the P6 meta-analysis model, or",
        "its substantive interpretation. All final analytic records remain subject to",
        "human verification and the documented data-lock workflow.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--markdown-out", type=Path)
    parser.add_argument("--r-tolerance", type=float, default=0.005)
    args = parser.parse_args()
    if args.r_tolerance < 0:
        parser.error("--r-tolerance must be non-negative")

    metrics = analyze(
        read_csv(args.gold, GOLD_REQUIRED),
        read_csv(args.predictions, PRED_REQUIRED),
        args.r_tolerance,
    )
    rendered_json = json.dumps(metrics, indent=2, ensure_ascii=False) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(rendered_json, encoding="utf-8")
    else:
        print(rendered_json, end="")
    if args.markdown_out:
        args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_out.write_text(markdown_report(metrics), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
