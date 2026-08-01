# Sampling frame v1 — provisional, not yet locked

`candidate_sample_v1.csv` contains **40 PRIMARY studies and 10 RESERVE
studies** selected deterministically from the P6 study database. The sampling
seed, source blob, normalized checksum, exclusions, OSF identifier and stratum
counts are recorded in `candidate_sample_v1.metadata.json`.

This is deliberately marked `PROVISIONAL`. It must not be described in the
thesis, defense or commercial material as a completed or locked validation
sample until every PRIMARY row passes both gates:

1. `full_text_status` is changed from `TO_CONFIRM` to `AVAILABLE` after the
   exact article file has been opened and checked;
2. `development_use` is changed from `TO_CONFIRM` to `NOT_USED` only after
   confirming the article was not used to develop, debug or tune M-AIDA or its
   prompt.

If a PRIMARY article fails either gate, replace it with the first eligible
RESERVE article from the same `dpl|icrv` stratum where possible. Record the
reason in `notes`; never silently delete an inconvenient case.

## Reproduce the candidate sample

Obtain the frozen source file identified in the metadata, then run:

```bash
python validation/select_validation_sample.py \
  --source /path/to/p6_study_database.csv \
  --demo-seed demo/demo_seed.csv \
  --output validation/sampling/candidate_sample_v1.csv \
  --metadata-out validation/sampling/candidate_sample_v1.metadata.json \
  --seed MAIDA-P6-VAL-20260801-01 \
  --primary 40 --reserve 10 \
  --source-repository thuyhuongctu/MY_THESIS_PHD_CANDIDATE_26 \
  --source-ref fix/p6-osf-integrity-20260801 \
  --source-path p6/data/p6_study_database.csv \
  --source-blob-sha 6f028a2e126cfa913297fdb9a4a41049221218d1
```

The selector excludes all Defense App seed studies and all study IDs with an
`is_estimated` record. It then performs deterministic stratified selection on
`DPL × ICRV`, with proportional allocation after guaranteeing PRIMARY coverage
of every non-empty stratum.

## Lock gate

After completing the two confirmations, run:

```bash
python validation/freeze_validation_sample.py \
  --manifest validation/sampling/candidate_sample_v1.csv \
  --metadata validation/sampling/candidate_sample_v1.metadata.json \
  --output validation/sampling/sample_lock.json
```

The command currently exits with code 2 and lists the blockers. A successful
lock records the manifest checksum and PRIMARY study IDs. Add the resulting
lock information to the OSF **addendum/deviation log** for Z37KN; do not
rewrite the historical OSF record as an a-priori preregistration.
