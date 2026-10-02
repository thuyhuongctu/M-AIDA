# Independent validation package

This directory turns `VALIDATION_PROTOCOL.md` into an executable, auditable
benchmark. It intentionally contains **no claimed performance results**. Real
results may be reported only after an independently coded sample has been
completed and the frozen files have been archived.

## Files

- `gold_standard_template.csv`: adjudicated human reference data, including
  the two coders' pre-adjudication decisions.
- `predictions_template.csv`: untouched M-AIDA proposals and verification
  timing for the same `case_id` values.
- `analyze_validation.py`: dependency-free analysis that validates both files
  and writes JSON plus Markdown reports.
- `tests/fixtures/`: synthetic records used only to test the analysis code.
- `sampling/candidate_sample_v1.csv`: deterministic 40-study PRIMARY frame
  plus 10 reserves; currently provisional.
- `select_validation_sample.py`: reproduces the stratified candidate frame.
- `freeze_validation_sample.py`: refuses to lock the frame until full-text and
  anti-development-overlap gates pass.
- `CODING_MANUAL_VI.md`: operational instructions for two blinded coders and
  adjudication.
- `run_benchmark.py`: runs the frozen extractor once over the locked sample
  and writes the run directory (manifest, untouched proposals, raw replies,
  matching and verification templates).
- `coding_workbooks.py`: candidate-effect enumeration workbook, the two coder
  workbooks, and their merge into a gold-standard draft plus disagreements.
- `build_predictions.py`: joins one run with the adjudicated gold standard into
  `predictions.csv` under pre-stated rules.
- `PROTOCOL_S6_DRAFT_VI.md`: draft revision of protocol section 6, pending the
  PI's decisions (frozen version, unit of analysis, enumeration, timing).
- `requirements.txt`: `openpyxl` for the workbooks; the analysis itself needs
  only the standard library.

## Workflow

Every step writes new files and refuses to overwrite existing ones.

```bash
pip install -r backend/requirements.txt -r validation/requirements.txt

# 1. after the frame is locked: list candidate effects by location only
python validation/coding_workbooks.py enumerate --lock validation/sampling/sample_lock_v1.json \
  --out validation/coding/case_enumeration.xlsx
# 2. two identical coder workbooks; each coder works blind on their own file
python validation/coding_workbooks.py coders --enumeration validation/coding/case_enumeration.xlsx \
  --out-dir validation/coding
# 3. merge; adjudicate disagreements.csv into a copy named validation/gold_standard.csv
python validation/coding_workbooks.py merge --coder1 validation/coding/coder1.xlsx \
  --coder2 validation/coding/coder2.xlsx --out-dir validation/coding
# 4. one frozen run (check first with --dry-run; LLM_MODEL and LLM_TEMPERATURE in backend/.env)
python validation/run_benchmark.py --pdf-dir <full-text folder> \
  --lock validation/sampling/sample_lock_v1.json --out validation/runs/<date> --operator <initials>
# 5. fill proposal_matches.csv and verification_log.csv in the run directory, then
python validation/build_predictions.py --gold validation/gold_standard.csv \
  --run validation/runs/<date> --out validation/runs/<date>/predictions.csv
```

`--rehearsal` lets `run_benchmark.py` try the pipeline on papers outside the
sample (unlocked frame, unset temperature); such runs are stamped REHEARSAL
and `build_predictions.py` refuses them.

## Run the analysis

```bash
python validation/analyze_validation.py \
  --gold validation/gold_standard.csv \
  --predictions validation/runs/<date>/predictions.csv \
  --json-out validation/results/validation_metrics.json \
  --markdown-out validation/results/VALIDATION_REPORT.md
```

The two input files come from steps 3 and 5 above (the templates in this
folder document their columns). Do not replace the template files with thesis
data. The script rejects duplicate, missing, or unexpected
`case_id` values and never modifies the source CSV files.

The generated report distinguishes machine proposals from PI-verified and
locked data. Passing software tests demonstrates that the metric calculations
work; it does **not** demonstrate that M-AIDA has met the research thresholds.

## Current execution status

Candidate selection is complete, but the frame is **not locked**. The next
human task is to confirm full-text availability and non-use during M-AIDA
development for each PRIMARY study. See `sampling/README.md`.
