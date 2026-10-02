#!/usr/bin/env python3
"""Run the frozen M-AIDA extractor once over the locked validation sample.

One PDF per study, one model call per PDF (plus retries only for provider
failures), exactly the code path the application uses: pypdfium2 text, the
same 40,000-character limit and page limit, the same prompt, the same
evidence gate. Nothing is tuned or re-run after the outputs are seen.

Outputs (in a NEW run directory; the script never overwrites one):

    run_manifest.json        software version, git commit, model, temperature,
                             prompt fingerprint, limits, lock-file checksum,
                             per-PDF SHA-256, outcome counts, tokens, timings
    proposals.csv            one row per study: outcome and the untouched
                             machine proposal (r, t, beta, df, n, route,
                             evidence page + verbatim quote, confidence, ...)
    raw/<study_id>.json      the raw model reply and the parsed record
    proposal_matches.csv     template: which gold candidate each proposal is
    verification_log.csv     template: PI verification minutes and decisions
    maida_validation.db      the proposals as M-AIDA records, so the PI can
                             verify them in the normal application

Typical use (from the repository root, backend/.env holding the key):

    # 1. check files and mapping without calling the model
    python validation/run_benchmark.py --pdf-dir D:/P6_fulltext --lock validation/sampling/sample_lock_v1.json \\
        --out validation/runs/2026-10-xx --dry-run
    # 2. the real run (temperature must be frozen explicitly)
    LLM_TEMPERATURE=0 python validation/run_benchmark.py --pdf-dir D:/P6_fulltext \\
        --lock validation/sampling/sample_lock_v1.json --out validation/runs/2026-10-xx --operator DTH

PDF files are matched to studies by file name: the name must start with the
study_id followed by a non-alphanumeric character or the extension
(``S139.pdf``, ``S139_Aulakh_2000.pdf``). Exactly one PDF per study.

``--rehearsal`` allows an unlocked frame and an unset temperature, for trying
the pipeline on non-sample papers; the manifest and every output are then
stamped REHEARSAL and build_predictions.py refuses to use them.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"

PROPOSAL_COLUMNS = [
    "paper_id", "label", "outcome", "error_code", "error_message", "record_id",
    "effect_r", "effect_t", "effect_beta", "effect_df", "n_predictors", "sample_n", "p_value",
    "ci_lower", "ci_upper", "predicted_route", "metric_type", "estimand_source",
    "doi_measure", "performance_measure", "extraction_confidence", "requires_verification",
    "evidence_page", "evidence_quote", "n_evidence_page", "n_evidence_quote", "provenance_present",
    "text_truncated", "pdf_file", "pdf_sha256", "pdf_pages", "text_chars",
    "input_tokens", "output_tokens", "latency_ms", "attempts", "finished_at_utc",
]
MATCH_COLUMNS = ["paper_id", "record_id", "match_status", "matched_case_id", "match_basis", "matcher_id", "notes"]
VERIFICATION_COLUMNS = ["paper_id", "outcome", "verifier_id", "verification_minutes", "fields_corrected", "hallucinated", "notes"]

FINAL_OUTCOMES = ("succeeded", "rejected")


@dataclass
class Paper:
    paper_id: str
    label: str
    year: int


class RecordingEngine:
    """Wraps the real engine and keeps the raw reply of the last call."""

    def __init__(self, inner: Any) -> None:
        self.inner = inner
        self.provider = getattr(inner, "provider", "")
        self.model = getattr(inner, "model", "")
        self.last_raw: str | None = None
        self.last_usage: dict[str, int] | None = None
        self.last_latency_ms: int = 0

    def complete(self, system: str, user: str, max_tokens: int = 1024) -> str:
        # Usage is taken only from a call that returned; a failed call never
        # inherits the token counts of the previous paper.
        self.last_raw, self.last_usage = None, None
        try:
            reply = self.inner.complete(system=system, user=user, max_tokens=max_tokens)
        finally:
            self.last_latency_ms = int(getattr(self.inner, "last_latency_ms", 0) or 0)
        self.last_usage = getattr(self.inner, "last_usage", None)
        self.last_raw = reply
        return reply


# ---------------------------------------------------------------------------
# inputs
# ---------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_papers(sampling_csv: Path, wanted: list[str] | None, group: str) -> list[Paper]:
    with sampling_csv.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    by_id = {r["study_id"].strip(): r for r in rows}
    if wanted is None:
        wanted = [r["study_id"].strip() for r in rows if r.get("selection_group") == group]
    papers = []
    for sid in wanted:
        row = by_id.get(sid)
        if row is None:
            raise SystemExit(f"study {sid} from the lock file is not in {sampling_csv}")
        papers.append(Paper(paper_id=sid, label=row.get("label", "").strip(), year=int(row.get("year") or 0)))
    return papers


def match_pdfs(pdf_dir: Path, papers: list[Paper]) -> tuple[dict[str, Path], list[str]]:
    files = sorted(p for p in pdf_dir.iterdir() if p.is_file() and p.suffix.lower() == ".pdf")
    found: dict[str, Path] = {}
    problems: list[str] = []
    for paper in papers:
        pattern = re.compile(rf"^{re.escape(paper.paper_id)}(?![A-Za-z0-9])", re.IGNORECASE)
        hits = [f for f in files if pattern.match(f.stem)]
        if not hits:
            problems.append(f"{paper.paper_id}: no PDF whose name starts with '{paper.paper_id}'")
        elif len(hits) > 1:
            problems.append(f"{paper.paper_id}: several PDFs match: " + ", ".join(h.name for h in hits))
        else:
            found[paper.paper_id] = hits[0]
    return found, problems


def app_version() -> str:
    """The packaged version (backend/pyproject.toml), without importing the app:
    importing main.py would open and migrate the application's own database."""
    import tomllib

    return tomllib.loads((BACKEND / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]


def git_state() -> dict[str, Any]:
    def run(*args: str) -> str:
        try:
            return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=20, check=True).stdout.strip()
        except Exception:  # noqa: BLE001 - git is optional
            return ""

    commit = run("rev-parse", "HEAD")
    dirty = run("status", "--porcelain", "--untracked-files=no")
    return {"commit": commit or None, "describe": run("describe", "--tags", "--always") or None,
            "tracked_changes": bool(dirty) if commit else None}


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------


def route_of(rec: dict[str, Any]) -> str:
    if rec.get("effect_r") is None:
        return ""
    source = rec.get("r_source")
    if source == "reported":
        return "direct_r"
    if source == "derived" and rec.get("effect_t") is not None:
        return "t_to_r"
    if source == "imputed" and rec.get("effect_beta") is not None:
        return "beta_to_r"
    return "other"


def proposal_row(paper: Paper, rec: dict[str, Any] | None) -> dict[str, Any]:
    row: dict[str, Any] = {c: "" for c in PROPOSAL_COLUMNS}
    row.update(paper_id=paper.paper_id, label=paper.label)
    if rec is None:
        return row
    for key in ("effect_r", "effect_t", "effect_beta", "effect_df", "n_predictors", "sample_n", "p_value",
                "ci_lower", "ci_upper", "metric_type", "estimand_source", "doi_measure", "performance_measure",
                "extraction_confidence", "requires_verification", "evidence_page", "evidence_quote",
                "n_evidence_page", "n_evidence_quote", "text_truncated"):
        value = rec.get(key)
        row[key] = "" if value is None else value
    row["record_id"] = rec.get("study_id", "")
    row["predicted_route"] = route_of(rec)
    row["provenance_present"] = bool(rec.get("evidence_quote") and rec.get("evidence_page") is not None
                                     and (rec.get("sample_n") is None or rec.get("n_evidence_quote")))
    return row


def write_csv(path: Path, columns: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: ("TRUE" if v is True else "FALSE" if v is False else v) for k, v in row.items()})


def refresh_template(path: Path, columns: list[str], machine: tuple[str, ...], fresh: list[dict[str, Any]]) -> None:
    """(Re)write a template the people fill in after the run.

    Untouched (every human column blank): rewritten from this run, so a
    resumed run lists the papers it completed. Once anyone has typed into it,
    existing rows are never changed; only papers missing from it are appended.
    """
    if path.exists():
        with path.open(encoding="utf-8-sig", newline="") as handle:
            existing = list(csv.DictReader(handle))
        human = [c for c in columns if c not in machine]
        if any((row.get(c) or "").strip() for row in existing for c in human):
            known = {row["paper_id"] for row in existing}
            added = [row for row in fresh if row["paper_id"] not in known]
            write_csv(path, columns, existing + added)
            print(f"[run_benchmark] {path.name} already has entries: kept them"
                  + (f", appended {len(added)} new paper(s)" if added else "") + "; check its rows against proposals.csv")
            return
    write_csv(path, columns, fresh)


def run(args: argparse.Namespace, engine_factory: Callable[[], Any] | None = None) -> int:
    sys.path.insert(0, str(BACKEND))
    os.chdir(BACKEND)  # backend/.env is read relative to the backend directory
    import settings as settings_module

    settings_module._settings = None
    settings = settings_module.get_settings()
    from extractor import (
        MAX_OUTPUT_TOKENS,
        PDF_TEXT_LIMIT,
        EvidenceMissingError,
        MalformedLLMOutputError,
        StatisticalExtractor,
        prompt_fingerprint,
    )
    from engines import EngineError, make_engine
    from fastapi import HTTPException
    from jobs import machine_proposal_snapshot, read_pdf_text
    from models import StudyDatabaseEntry

    out: Path = args.out
    lock_info: dict[str, Any] | None = None
    if args.lock:
        lock_info = json.loads(args.lock.read_text(encoding="utf-8"))
        if lock_info.get("status") != "LOCKED":
            raise SystemExit(f"{args.lock} is not a LOCKED sampling frame")
        wanted = list(lock_info["primary_study_ids"])
    elif args.rehearsal:
        wanted = None
    else:
        raise SystemExit("--lock is required (run validation/freeze_validation_sample.py first); use --rehearsal to try the pipeline")

    papers = load_papers(args.sampling, wanted, args.group)
    if args.only:
        keep = set(args.only)
        papers = [p for p in papers if p.paper_id in keep]
    pdfs, problems = match_pdfs(args.pdf_dir, papers)

    temperature = settings.llm_temperature
    if args.temperature is not None:
        temperature = args.temperature
    model_id = settings.resolved_model
    if not args.rehearsal:
        if temperature is None:
            problems.append("temperature is not frozen: set LLM_TEMPERATURE (recommended 0) or pass --temperature")
        if not model_id:
            problems.append("LLM_MODEL is empty: pin the model id explicitly for a validation run")
        git = git_state()
        if git["commit"] is None:
            print("[run_benchmark] WARNING  not a git checkout: the manifest can name the version but not the commit")
        elif git["tracked_changes"]:
            problems.append("tracked files have uncommitted changes: a validation run must use a committed version")

    print(f"[run_benchmark] {len(papers)} studies, {len(pdfs)} PDFs matched, model={model_id or '(adapter default)'}, "
          f"temperature={temperature if temperature is not None else 'provider default'}, prompt={prompt_fingerprint()}")
    for problem in problems:
        print(f"[run_benchmark] PROBLEM  {problem}")

    if args.dry_run:
        for paper in papers:
            pdf = pdfs.get(paper.paper_id)
            if pdf is None:
                continue
            try:
                text = read_pdf_text(pdf.read_bytes(), max_pages=settings.maida_max_pages)
                flag = " (text beyond the 40,000-character limit)" if len(text.text) > PDF_TEXT_LIMIT else ""
                if len(text.text.strip()) < 500:
                    flag += " (little or no text layer: scanned PDF?)"
                print(f"[run_benchmark] ok       {paper.paper_id}: {pdf.name}, {text.pages} pages, {len(text.text)} chars{flag}")
            except HTTPException as exc:
                print(f"[run_benchmark] PROBLEM  {paper.paper_id}: {exc.detail}")
                problems.append(f"{paper.paper_id}: {exc.detail}")
        print("[run_benchmark] dry run: no model call made." + (" Fix the problems above first." if problems else ""))
        return 2 if problems else 0

    if problems:
        print("[run_benchmark] not started; fix the problems above.")
        return 2

    resume = args.resume and out.exists()
    if out.exists() and not resume:
        raise SystemExit(f"{out} already exists; choose a new run directory (outputs are never overwritten) or pass --resume")
    # The frozen configuration is written before the first call; a resumed
    # run must match it exactly, so one run directory = one configuration.
    frozen = {
        "kind": "REHEARSAL" if args.rehearsal else "VALIDATION_RUN",
        "version": app_version(),
        "git_commit": git_state()["commit"],
        "model_provider": settings.llm_provider,
        "model_identifier": model_id,
        "temperature": temperature,
        "prompt_version": prompt_fingerprint(),
        "pdf_text_limit_chars": PDF_TEXT_LIMIT,
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "max_pages": settings.maida_max_pages,
        "sampling_lock_sha256": sha256_file(args.lock) if args.lock else None,
    }
    config_path = out / "run_config.json"
    if resume:
        if not config_path.exists():
            raise SystemExit(f"{out} has no run_config.json; it is not a run directory written by this script")
        previous = json.loads(config_path.read_text(encoding="utf-8"))
        changed = sorted(k for k in frozen if k != "started_at_utc" and previous.get(k) != frozen[k])
        if changed:
            raise SystemExit("cannot resume: the configuration differs from the interrupted run in "
                             + ", ".join(f"{k} ({previous.get(k)!r} -> {frozen[k]!r})" for k in changed)
                             + ". Start a new run directory instead.")
        frozen["started_at_utc"] = previous["started_at_utc"]
    else:
        frozen["started_at_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    (out / "raw").mkdir(parents=True, exist_ok=True)
    if not resume:
        config_path.write_text(json.dumps(frozen, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if engine_factory is None:
        def engine_factory() -> Any:
            if not settings.anthropic_api_key:
                raise SystemExit("LLM_API_KEY is not configured in backend/.env")
            return make_engine(settings.llm_provider, api_key=settings.anthropic_api_key,
                               model=model_id, temperature=temperature)

    engine = RecordingEngine(engine_factory())
    extractor = StatisticalExtractor(engine=engine)
    store = None
    if not args.no_store:
        from store import StudyStore

        store = StudyStore(out / "maida_validation.db")

    started = datetime.fromisoformat(frozen["started_at_utc"])
    rows: list[dict[str, Any]] = []
    pdf_hashes: dict[str, str] = {}
    totals = {"input_tokens": 0, "output_tokens": 0}
    for index, paper in enumerate(papers, start=1):
        pdf = pdfs[paper.paper_id]
        raw_path = out / "raw" / f"{paper.paper_id}.json"
        if resume and raw_path.exists():
            saved = json.loads(raw_path.read_text(encoding="utf-8"))
            if saved.get("outcome") in FINAL_OUTCOMES:
                rows.append(saved["proposal_row"])
                pdf_hashes[paper.paper_id] = saved["proposal_row"]["pdf_sha256"]
                for k in totals:
                    totals[k] += int(saved["proposal_row"].get(k) or 0)
                print(f"[run_benchmark] {index:>2}/{len(papers)} {paper.paper_id}: kept from previous run ({saved['outcome']})")
                continue
        data = pdf.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        pdf_hashes[paper.paper_id] = digest
        metadata = {"title": "", "authors": paper.label, "year": paper.year, "country": "", "filename": pdf.name}
        record: dict[str, Any] | None = None
        outcome, code, message = "failed", "", ""
        attempts = 0
        pages = chars = ""
        try:
            text = read_pdf_text(data, max_pages=settings.maida_max_pages)
            pages, chars = text.pages, len(text.text)
        except HTTPException as exc:
            text = None
            outcome, code, message = "failed", "pdf_unreadable", str(exc.detail)
        while text is not None and attempts <= args.retries:
            attempts += 1
            try:
                effect = extractor.extract_from_text(text.text, metadata)
                entry = StudyDatabaseEntry(**effect.model_dump())
                entry.study_id = f"VAL-{paper.paper_id}"
                entry.machine_proposal = machine_proposal_snapshot(effect)
                record = json.loads(entry.model_dump_json())
                outcome, code, message = "succeeded", "", ""
                if store is not None:
                    store.put(entry)
                break
            except EvidenceMissingError as exc:
                outcome, code, message = "rejected", "evidence_missing", str(exc)
                break
            except MalformedLLMOutputError as exc:
                outcome, code, message = "rejected", "malformed_output", str(exc)
                break
            except EngineError as exc:
                outcome, code, message = "failed", "provider_error", str(exc)
                if attempts <= args.retries:
                    time.sleep(args.retry_wait)
            except Exception as exc:  # noqa: BLE001 - record it, keep the batch going, resume retries it
                outcome, code, message = "failed", "internal_error", f"{type(exc).__name__}: {exc}"
                break
        usage = engine.last_usage or {}
        row = proposal_row(paper, record)
        row.update(outcome=outcome, error_code=code, error_message=message[:500], pdf_file=pdf.name,
                   pdf_sha256=digest, pdf_pages=pages, text_chars=chars,
                   input_tokens=int(usage.get("input_tokens", 0) or 0), output_tokens=int(usage.get("output_tokens", 0) or 0),
                   latency_ms=engine.last_latency_ms, attempts=attempts,
                   finished_at_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"))
        for k in totals:
            totals[k] += int(row[k] or 0)
        rows.append(row)
        raw_path.write_text(json.dumps({
            "paper_id": paper.paper_id, "outcome": outcome, "error_code": code, "error_message": message,
            "raw_model_reply": engine.last_raw, "record": record, "proposal_row": row,
            "rehearsal": bool(args.rehearsal),
        }, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
        shown = f"r = {row['effect_r']}, n = {row['sample_n']}" if outcome == "succeeded" else f"{code}"
        print(f"[run_benchmark] {index:>2}/{len(papers)} {paper.paper_id}: {outcome} ({shown})")

    finished = datetime.now(timezone.utc)
    write_csv(out / "proposals.csv", PROPOSAL_COLUMNS, rows)
    match_path, verify_path = out / "proposal_matches.csv", out / "verification_log.csv"
    refresh_template(match_path, MATCH_COLUMNS, ("paper_id", "record_id"), [
        {"paper_id": r["paper_id"], "record_id": r["record_id"]}
        for r in rows if r["outcome"] == "succeeded" and r["effect_r"] != ""])
    refresh_template(verify_path, VERIFICATION_COLUMNS, ("paper_id", "outcome"), [
        {"paper_id": r["paper_id"], "outcome": r["outcome"]} for r in rows])

    counts: dict[str, int] = {}
    for r in rows:
        counts[r["outcome"]] = counts.get(r["outcome"], 0) + 1
    import importlib.metadata as md

    def version_of(pkg: str) -> str | None:
        try:
            return md.version(pkg)
        except md.PackageNotFoundError:
            return None

    version = app_version()
    manifest = {
        "kind": "REHEARSAL" if args.rehearsal else "VALIDATION_RUN",
        "software": "M-AIDA: Meta-Analysis Intelligent Data Assistant",
        "version": version,
        "git": git_state(),
        "model_provider": settings.llm_provider,
        "model_identifier": getattr(engine, "model", "") or model_id,
        "temperature": temperature,
        "prompt_version": prompt_fingerprint(),
        "pdf_text_limit_chars": PDF_TEXT_LIMIT,
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "max_pages": settings.maida_max_pages,
        "metadata_sent": "authors = sampling-frame label, year; title and country left blank",
        "retries_on_provider_error": args.retries,
        "extraction_date": started.date().isoformat(),
        "started_at_utc": started.isoformat(timespec="seconds"),
        "finished_at_utc": finished.isoformat(timespec="seconds"),
        "operator": args.operator,
        "sampling_frame": str(args.sampling.relative_to(ROOT)) if args.sampling.is_relative_to(ROOT) else str(args.sampling),
        "sampling_lock": None if lock_info is None else {
            "path": str(args.lock), "sha256": sha256_file(args.lock),
            "selection_fingerprint_sha256": lock_info.get("selection_fingerprint_sha256"),
        },
        "studies": len(rows),
        "outcomes": counts,
        "tokens": totals,
        "estimated_cost_usd": round(
            (totals["input_tokens"] * settings.llm_price_input_per_mtok
             + totals["output_tokens"] * settings.llm_price_output_per_mtok) / 1_000_000, 4),
        "pdf_sha256": pdf_hashes,
        "environment": {"python": platform.python_version(), "platform": platform.platform(),
                        "anthropic": version_of("anthropic"), "pypdfium2": version_of("pypdfium2")},
        "human_verifier": "TO_BE_FILLED_AT_VERIFICATION",
        "lock_status": "machine proposals only; nothing verified or locked yet",
    }
    (out / "run_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if store is not None:
        store.close()
    print(f"[run_benchmark] done: {counts}; tokens in/out {totals['input_tokens']}/{totals['output_tokens']}; "
          f"estimated ${manifest['estimated_cost_usd']}; outputs in {out}")
    return 0 if counts.get("failed", 0) == 0 else 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pdf-dir", type=Path, required=True, help="folder holding one PDF per study (name starts with the study_id)")
    ap.add_argument("--out", type=Path, required=True, help="new run directory, e.g. validation/runs/2026-10-15")
    ap.add_argument("--lock", type=Path, help="sampling lock JSON written by freeze_validation_sample.py")
    ap.add_argument("--sampling", type=Path, default=ROOT / "validation" / "sampling" / "candidate_sample_v1.csv")
    ap.add_argument("--group", default="PRIMARY", help="selection group used with --rehearsal (default PRIMARY)")
    ap.add_argument("--only", nargs="*", help="restrict to these study ids (rehearsal or resume of a few papers)")
    ap.add_argument("--temperature", type=float, help="overrides LLM_TEMPERATURE for this run")
    ap.add_argument("--retries", type=int, default=2, help="retries per study on provider errors only (default 2)")
    ap.add_argument("--retry-wait", type=float, default=20.0, help="seconds between retries (default 20)")
    ap.add_argument("--operator", default="", help="initials of the person running the batch")
    ap.add_argument("--dry-run", action="store_true", help="check files, mapping and text layers; no model call")
    ap.add_argument("--resume", action="store_true", help="continue an interrupted run in the same --out directory")
    ap.add_argument("--rehearsal", action="store_true", help="allow an unlocked frame / unset temperature; outputs stamped REHEARSAL")
    ap.add_argument("--no-store", action="store_true", help="do not write maida_validation.db")
    args = ap.parse_args(argv)
    args.out = args.out.resolve()
    args.pdf_dir = args.pdf_dir.resolve()
    args.sampling = args.sampling.resolve()
    if args.lock:
        args.lock = args.lock.resolve()
    if not args.pdf_dir.is_dir():
        ap.error(f"--pdf-dir {args.pdf_dir} is not a folder")
    return args


if __name__ == "__main__":
    raise SystemExit(run(parse_args()))
