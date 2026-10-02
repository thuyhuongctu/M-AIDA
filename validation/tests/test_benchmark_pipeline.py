"""End-to-end check of the validation tooling on synthetic papers.

run_benchmark (fake engine) -> coding workbooks (enumerate, coders, merge)
-> adjudicated gold -> build_predictions -> analyze_validation.

Every number below is synthetic and only exercises the plumbing.
"""

from __future__ import annotations

import csv
import json
import re
import shutil
import sys
from pathlib import Path

import pytest

openpyxl = pytest.importorskip("openpyxl")

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "tests"))

from conftest import make_minimal_pdf  # noqa: E402  (backend/tests helper)

from validation import build_predictions, coding_workbooks, run_benchmark  # noqa: E402
from validation.analyze_validation import GOLD_REQUIRED, PRED_REQUIRED, analyze, read_csv  # noqa: E402


class FakeEngine:
    """Quotes "r = x (n = y)" from the text; no statistics -> no evidence."""

    provider = "fake"
    model = "fake-validation-model"

    def __init__(self, fail_marker: str | None = None) -> None:
        self.fail_marker = fail_marker
        self.last_usage = None
        self.last_latency_ms = 0
        self.calls = 0

    def complete(self, system: str, user: str, max_tokens: int = 1024) -> str:
        from engines import EngineError

        self.calls += 1
        self.last_usage = None
        if self.fail_marker and self.fail_marker in user:
            raise EngineError("synthetic provider outage")
        self.last_usage = {"input_tokens": 1000, "output_tokens": 100}
        self.last_latency_ms = 7
        m = re.search(r"r = (-?[\d.]+) \(n = (\d+)\)", user)
        if not m:
            return json.dumps({"effect_r": 0.2, "sample_n": 10})
        return json.dumps({
            "effect_r": float(m.group(1)), "sample_n": int(m.group(2)),
            "evidence_page": 1, "evidence_quote": m.group(0),
            "n_evidence_page": 1, "n_evidence_quote": f"n = {m.group(2)}",
            "doi_measure": "FSTS", "performance_measure": "ACC", "extraction_confidence": 0.9,
        })


PAPERS = {
    "P1": "Results. The FSTS-ROA correlation is r = 0.31 (n = 200).",
    "P2": "Results. We find a positive association but report no usable statistic.",
    "P3": "FAILME Results. Breadth and Tobin's q: r = -0.12 (n = 150).",
}


@pytest.fixture()
def study(tmp_path, monkeypatch):
    monkeypatch.chdir(ROOT)  # run() changes directory; this restores it afterwards
    monkeypatch.setenv("LLM_MODEL", "fake-validation-model")
    monkeypatch.setenv("LLM_TEMPERATURE", "0")
    monkeypatch.setattr(run_benchmark, "git_state",
                        lambda: {"commit": "0" * 40, "describe": "v8.0.0", "tracked_changes": False})
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()
    for pid, text in PAPERS.items():
        (pdf_dir / f"{pid}_synthetic.pdf").write_bytes(make_minimal_pdf(text))
    sampling = tmp_path / "sample.csv"
    with sampling.open("w", encoding="utf-8", newline="") as h:
        w = csv.DictWriter(h, fieldnames=["selection_group", "study_id", "label", "year"])
        w.writeheader()
        for i, pid in enumerate(PAPERS, start=1):
            w.writerow({"selection_group": "PRIMARY", "study_id": pid, "label": f"Author {i} 2020", "year": 2020})
        w.writerow({"selection_group": "RESERVE", "study_id": "R1", "label": "Reserve", "year": 2019})
    lock = tmp_path / "lock.json"
    lock.write_text(json.dumps({"status": "LOCKED", "primary_study_ids": list(PAPERS),
                                "selection_fingerprint_sha256": "f" * 64}), encoding="utf-8")
    yield {"tmp": tmp_path, "pdf_dir": pdf_dir, "sampling": sampling, "lock": lock}
    import settings as settings_module

    settings_module._settings = None


def _args(study, out: Path, *extra: str):
    return run_benchmark.parse_args([
        "--pdf-dir", str(study["pdf_dir"]), "--sampling", str(study["sampling"]),
        "--lock", str(study["lock"]), "--out", str(out), "--retry-wait", "0", "--operator", "TEST", *extra])


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as h:
        return list(csv.DictReader(h))


def _write(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as h:
        w = csv.DictWriter(h, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def test_guards_before_any_model_call(study, monkeypatch):
    out = study["tmp"] / "run"
    assert run_benchmark.run(_args(study, out, "--dry-run")) == 0
    assert not out.exists()
    monkeypatch.delenv("LLM_TEMPERATURE")
    engine = FakeEngine()
    assert run_benchmark.run(_args(study, out), engine_factory=lambda: engine) == 2
    assert engine.calls == 0 and not out.exists()
    with pytest.raises(SystemExit, match="LOCKED"):
        study["lock"].write_text(json.dumps({"status": "PROVISIONAL", "primary_study_ids": []}))
        run_benchmark.run(_args(study, out), engine_factory=FakeEngine)


def test_full_pipeline_to_metrics(study, monkeypatch):
    tmp, out = study["tmp"], study["tmp"] / "run"

    # 1. the batch: P3 hits a provider outage, the run reports failure
    assert run_benchmark.run(_args(study, out), engine_factory=lambda: FakeEngine("FAILME")) == 1
    first = {r["paper_id"]: r for r in _rows(out / "proposals.csv")}
    assert [first[p]["outcome"] for p in PAPERS] == ["succeeded", "rejected", "failed"]
    assert first["P3"]["attempts"] == "3"  # 1 + 2 retries, provider errors only
    assert first["P3"]["input_tokens"] == "0"  # a failed call never inherits the previous paper's usage
    with pytest.raises(SystemExit, match="already exists"):
        run_benchmark.run(_args(study, out), engine_factory=FakeEngine)
    # a resume must keep the frozen configuration
    with pytest.raises(SystemExit, match="temperature"):
        run_benchmark.run(_args(study, out, "--resume", "--temperature", "0.5"), engine_factory=FakeEngine)
    engine = FakeEngine()
    assert run_benchmark.run(_args(study, out, "--resume"), engine_factory=lambda: engine) == 0
    assert engine.calls == 1  # only P3 is re-run
    proposals = {r["paper_id"]: r for r in _rows(out / "proposals.csv")}
    assert proposals["P1"]["effect_r"] == "0.31" and proposals["P1"]["predicted_route"] == "direct_r"
    assert proposals["P2"]["error_code"] == "evidence_missing"
    assert proposals["P3"]["effect_r"] == "-0.12" and proposals["P3"]["provenance_present"] == "TRUE"
    manifest = json.loads((out / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["kind"] == "VALIDATION_RUN" and manifest["temperature"] == 0
    assert manifest["prompt_version"].startswith("sha256:") and manifest["outcomes"] == {"succeeded": 2, "rejected": 1}
    assert set(manifest["pdf_sha256"]) == set(PAPERS)
    assert [r["paper_id"] for r in _rows(out / "proposal_matches.csv")] == ["P1", "P3"]

    # 2. enumeration of candidate effects (locations only)
    coding = tmp / "coding"
    enum_path = coding / "case_enumeration.xlsx"
    assert coding_workbooks.main(["enumerate", "--lock", str(study["lock"]), "--sampling", str(study["sampling"]),
                                  "--rows-per-paper", "2", "--out", str(enum_path)]) == 0
    wb = openpyxl.load_workbook(enum_path)
    ws = wb["Cases"]
    locs = {("P1", "E1"): "p.1 Table 2, FSTS-ROA", ("P1", "E2"): "p.1 Table 2, firm age (control)",
            ("P2", "E1"): "p.1 Table 3, Model 2, GEO", ("P3", "E1"): "p.1 Table 2, breadth-Q",
            ("P3", "E2"): "p.1 Table 4, size (control)"}
    order = list(locs)
    for row, key in zip(range(2, 8), [order[0], order[1], order[2], None, order[3], order[4]], strict=True):
        assert ws.cell(row=row, column=1).value == ["P1", "P1", "P2", "P2", "P3", "P3"][row - 2]
        if key is not None:
            ws.cell(row=row, column=4, value=key[1])
            ws.cell(row=row, column=5, value=locs[key])
    wb.save(enum_path)

    # 3. two coder workbooks; coder 2 disagrees on one scope decision
    assert coding_workbooks.main(["coders", "--enumeration", str(enum_path), "--out-dir", str(coding)]) == 0
    codes = {
        "P1-E1": ("TRUE", "direct_r", 0.310, 200, "FSTS", "ACC", 12),
        "P1-E2": ("FALSE", None, None, None, None, None, 3),
        "P2-E1": ("TRUE", "t_to_r", 0.250, 120, "GEO", "ACC", 15),
        "P3-E1": ("TRUE", "direct_r", -0.120, 150, "EXP", "MKT", 10),
        "P3-E2": ("FALSE", None, None, None, None, None, 2),
    }
    for coder, cid in (("coder1", "DTH"), ("coder2", "C2")):
        path = coding / f"{coder}.xlsx"
        wb = openpyxl.load_workbook(path)
        ws = wb["Coding"]
        for row in range(2, ws.max_row + 1):
            case = ws.cell(row=row, column=1).value
            values = list(codes[case])
            if coder == "coder2" and case == "P3-E2":
                values = ["TRUE", "direct_r", 0.05, 150, "EXP", "ACC", 4]
            if coder == "coder2" and case == "P2-E1":
                values[2] = 0.252  # within the 0.005 tolerance: agreement
            for col, value in enumerate(values, start=5):
                ws.cell(row=row, column=col, value=value)
        wb["Coder"]["B2"] = cid
        if coder == "coder1":
            wb.save(path)
            with pytest.raises(SystemExit, match="completed"):
                coding_workbooks.main(["merge", "--coder1", str(path), "--coder2", str(coding / "coder2.xlsx"),
                                       "--out-dir", str(coding)])
        wb["Coder"]["B3"] = "TRUE"
        wb.save(path)
    assert coding_workbooks.main(["merge", "--coder1", str(coding / "coder1.xlsx"),
                                  "--coder2", str(coding / "coder2.xlsx"), "--out-dir", str(coding)]) == 0
    draft = {r["case_id"]: r for r in _rows(coding / "gold_standard_draft.csv")}
    disagreements = _rows(coding / "disagreements.csv")
    assert [d["case_id"] for d in disagreements] == ["P3-E2"] and disagreements[0]["fields"] == "in_scope"
    assert draft["P2-E1"]["gold_r"] == "0.250" and draft["P3-E2"]["gold_in_scope"] == ""

    # 4. adjudication in a copy: P3-E2 is a control, out of scope
    gold_path = tmp / "gold_standard.csv"
    shutil.copy(coding / "gold_standard_draft.csv", gold_path)
    gold_rows = _rows(gold_path)
    for g in gold_rows:
        if g["case_id"] == "P3-E2":
            g.update(gold_in_scope="FALSE", adjudication_notes="control variable; out of scope")
    _write(gold_path, gold_rows)

    # 5. matching and verification log, then predictions
    pred_path = out / "predictions.csv"
    with pytest.raises(SystemExit, match="not been matched|match_status"):
        build_predictions.main(["--gold", str(gold_path), "--run", str(out), "--out", str(pred_path)])
    matches = _rows(out / "proposal_matches.csv")
    for m in matches:
        m.update(match_status="MATCHED", matched_case_id=f"{m['paper_id']}-E1", match_basis="table location",
                 matcher_id="DTH")
    _write(out / "proposal_matches.csv", matches)
    log = _rows(out / "verification_log.csv")
    times = {"P1": ("4", "0", "FALSE"), "P2": ("15", "", ""), "P3": ("3", "1", "FALSE")}
    for v in log:
        minutes, corrected, halluc = times[v["paper_id"]]
        v.update(verifier_id="DTH", verification_minutes=minutes, fields_corrected=corrected, hallucinated=halluc)
    _write(out / "verification_log.csv", log)
    assert build_predictions.main(["--gold", str(gold_path), "--run", str(out), "--out", str(pred_path)]) == 0
    with pytest.raises(SystemExit, match="exists"):
        build_predictions.main(["--gold", str(gold_path), "--run", str(out), "--out", str(pred_path)])

    # 6. the analysis accepts the files and the numbers follow by hand
    metrics = analyze(read_csv(gold_path, GOLD_REQUIRED), read_csv(pred_path, PRED_REQUIRED), tolerance=0.005)
    assert metrics["selection"]["confusion_matrix"] == {"tp": 2, "fp": 0, "fn": 1, "tn": 2}
    assert metrics["selection"]["recall"] == pytest.approx(2 / 3)
    assert metrics["field_accuracy"]["r_exact"]["value"] == pytest.approx(1.0)
    assert metrics["field_accuracy"]["route_exact"]["value"] == pytest.approx(1.0)
    assert metrics["field_accuracy"]["doi_measure_exact"]["value"] == pytest.approx(0.5)
    assert metrics["time"]["manual_minutes_mean"] == pytest.approx(42 / 5)
    assert metrics["time"]["assisted_verification_minutes_mean"] == pytest.approx(22 / 5)
    assert metrics["human_coder_agreement"]["in_scope_cohen_kappa"] == pytest.approx(0.24 / 0.44)
    assert metrics["governance"]["machine_proposal_correction_rate"]["value"] == pytest.approx(0.5)
    assert metrics["run_configuration"]["temperature"] == 0.0


def test_rehearsal_runs_are_never_used(study, monkeypatch):
    out = study["tmp"] / "rehearsal"
    monkeypatch.delenv("LLM_TEMPERATURE")
    args = run_benchmark.parse_args(["--pdf-dir", str(study["pdf_dir"]), "--sampling", str(study["sampling"]),
                                     "--out", str(out), "--rehearsal", "--only", "P1", "--no-store"])
    assert run_benchmark.run(args, engine_factory=FakeEngine) == 0
    assert json.loads((out / "run_manifest.json").read_text())["kind"] == "REHEARSAL"
    assert not (out / "maida_validation.db").exists()
    with pytest.raises(SystemExit, match="REHEARSAL"):
        build_predictions.build(study["tmp"] / "unused.csv", out)


def test_incomplete_enumeration_is_refused(study):
    path = study["tmp"] / "enum.xlsx"
    coding_workbooks.main(["enumerate", "--lock", str(study["lock"]), "--sampling", str(study["sampling"]),
                           "--rows-per-paper", "1", "--out", str(path)])
    wb = openpyxl.load_workbook(path)
    wb["Cases"].cell(row=2, column=5, value="p.1 Table 2")  # P1 listed; P2 and P3 left empty
    wb.save(path)
    with pytest.raises(SystemExit, match="P2: no candidate effect listed"):
        coding_workbooks.read_enumeration(path)
