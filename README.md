# M-AIDA: Meta-Analysis Intelligent Data Assistant

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21282516.svg)](https://doi.org/10.5281/zenodo.21282516)
![version](https://img.shields.io/badge/version-7.1.1-blue) ![python](https://img.shields.io/badge/python-FastAPI-green) ![frontend](https://img.shields.io/badge/frontend-React%2018%20%2B%20TS-61dafb) ![license](https://img.shields.io/badge/license-Academic%20Source--Available-lightgrey)

Research software for meta-analysis: semi-automated effect-size extraction from
academic PDFs with a vendor-neutral large-language-model adapter, human-in-the-loop
verification by the principal investigator, and an immutable data-lock workflow that
exports a reproducible effect-size dataset for three-level meta-analytic regression.

**Authors**

- Do Thuy Huong ([ORCID 0000-0002-7711-2487](https://orcid.org/0000-0002-7711-2487)), PhD Candidate, School of Economics, Can Tho University.
- Phan Anh Tu ([ORCID 0000-0003-0667-3137](https://orcid.org/0000-0003-0667-3137)), School of Economics, Can Tho University.

Built to support the P6 (meta-analysis) component of the first author's doctoral
dissertation on the internationalization-performance relationship.

## System Architecture

```text
frontend (React 18, :3000)
    calls --> backend (FastAPI, :8765)
                 |-- extractor.py    vendor-neutral LLM parsing
                 |-- engines.py      provider adapter (LLM_PROVIDER / LLM_API_KEY / LLM_MODEL)
                 |-- models.py       Pydantic domain models
                 |-- notion_sync.py  optional Notion database sync
```

The language model is reached through a configurable adapter. Set `LLM_PROVIDER`,
`LLM_API_KEY` and `LLM_MODEL` to your own provider; the software is not tied to any
single vendor.

## Quick Start

```bash
# 1. Configure environment
cp backend/.env.example backend/.env
# Edit backend/.env: LLM_PROVIDER, LLM_API_KEY, LLM_MODEL, NOTION_TOKEN, NOTION_DATABASE_ID

# 2. Start with Docker Compose
docker compose up

# 3. Open the app
open http://localhost:3000
```

## One-command live demo (no Docker, no Node)

For demonstrations (e.g. a thesis defense) the repository ships a packaging
harness that starts the real backend pre-seeded with real effect-size records
from the dissertation's locked P6 database and serves a dependency-free web
console at the same port. No response is simulated; every action goes through
the live API.

```bash
pip install -r backend/requirements.txt
python demo/run_defense.py
# open http://localhost:8765/  (interactive API docs at /docs)
```

Seeding rules and options (full-database seed, lock-all mode) are documented in
`demo/run_defense.py`; a Vietnamese walkthrough for the defense session is in
`demo/HUONG_DAN_BAO_VE.md`. Live PDF extraction additionally requires
`LLM_API_KEY` in `backend/.env`; without it the extraction endpoint returns an
explicit 503 and all other features work offline.

## Development and tests

```bash
# Backend unit tests (effect-size conversions + confidence scheme)
cd backend
pip install -e ".[test]"
pytest -q

# Frontend (Vite): dev server / production build
cd frontend
npm ci
npm run dev      # http://localhost:3000
npm run build    # outputs to build/
```

CI runs the backend test suite and the frontend Vite build on every change.
Set `VITE_API_URL` (see `frontend/.env.example`) to point the client at a
non-default backend URL.

## API Routes

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/extract` | Base64 PDF body to an extracted effect size |
| POST | `/api/extract/upload` | Multipart PDF upload to an extracted effect size |
| GET | `/api/studies` | List studies (filter: icrv, dpl, verified, locked) |
| GET | `/api/studies/{id}` | Single study detail |
| PATCH | `/api/studies/{id}/verify` | PI field overrides and approval |
| POST | `/api/studies/{id}/lock` | Irreversible PI data lock |
| GET | `/api/studies/export/csv` | Export locked studies as CSV |
| POST | `/api/notion/sync` | Push locked studies to Notion |
| GET | `/api/health` | Health check and service configuration flags |

## Extraction Workflow

1. **Parse**: PDF text is extracted with MuPDF and segmented into statistical regions.
2. **Identify**: the LLM adapter proposes the focal internationalization-performance
   coefficient (not interactions or controls). Moderators (ICRV, DPL, cDAI) are left
   blank for the principal investigator to assign from external lookup tables.
3. **Convert**: the canonical target is Pearson r. When only a derived statistic is
   reported, r is computed from t using Cohen (1988), or from a standardized beta
   using Peterson and Brown (2005). A three-level confidence score is attached.
4. **Verify**: the principal investigator reviews each field; any record with
   confidence below 0.70 is flagged for mandatory review.
5. **Lock**: an approved record is permanently locked with a UTC timestamp and can no
   longer be edited. Only locked records enter the analysis export.

## Live web pages (GitHub Pages)

The repository is also served as a static site with three linked pages:

- **Main page** ([index.html](https://thuyhuongctu.github.io/M-AIDA/)): overview,
  positioning, the interactive atlas of 236 studies, the in-browser extraction
  console, and the Huong AI tour guide. Bilingual EN/VI.
- **Commercial page** ([commercial.html](https://thuyhuongctu.github.io/M-AIDA/commercial.html)):
  productization and licensing overview.
- **Data & Melody** ([data_melody.html](https://thuyhuongctu.github.io/M-AIDA/data_melody.html)):
  the story of the software told as a guided walk with Huong AI, in Vietnamese,
  English, and French.

**Theme song.** The mood menu on the main and commercial pages ("Nothing" option)
plays the M-AIDA anthem *"Je m'appelle Huong - M-AIDA, mon histoire"*
(`assets/maida_song.mp3`, take 2). Lyrics were written by Do Thuy Huong
(17 July 2026); the music and recording were generated with AI assistance, so
authorship claims attach to the lyrics, not the audio.

## Citation

If you use M-AIDA, please cite it (GitHub renders a "Cite this repository" button
from `CITATION.cff`):

> Do, T. H., and Phan, A. T. (2026). *M-AIDA: Meta-Analysis Intelligent Data Assistant* (Version 7.1.1)
> [Computer software]. Can Tho University. https://doi.org/10.5281/zenodo.21282516

Zenodo mints two identifiers: the concept DOI `10.5281/zenodo.21282516` always
resolves to the latest version, while the version DOI `10.5281/zenodo.21282517`
pins release v7.1.1. Cite the concept DOI for the software in general and the
version DOI for an exact reproducible build.

## Authorship, license, and research-integrity note

**Authors and copyright holders:** Do Thuy Huong and Phan Anh Tu, School of Economics,
Can Tho University. Copyright subsists automatically under Vietnamese law and the Berne
Convention from the moment of creation; a Copyright Office of Viet Nam registration is
being prepared with Can Tho University as a co-owner under the university's
intellectual-property regulations.

**Role of computational assistance:** M-AIDA uses a configurable language-model provider
only to *propose* candidate effect sizes and statistical conversions from study text. It
is a human-in-the-loop tool: every proposed value must be independently verified,
corrected if needed, and permanently locked by the principal investigator before it
enters the analysis database. The provider does not select studies, decide eligibility,
run the meta-analysis, write interpretive content, or hold authorship or ownership over
the software. Scientific responsibility remains with the named human authors.

**Security:** copy `backend/.env.example` to `backend/.env` and supply your own keys;
never commit a real `.env` (it is git-ignored).

## License

Academic Source-Available License: see `LICENSE`. The software is public for
transparency, citation, and academic verification; all rights are reserved by the
authors under automatic copyright.
