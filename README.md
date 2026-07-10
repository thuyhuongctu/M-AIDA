# M-AIDA v7.1: Meta-Analysis Intelligent Data Assistant

Developed at Can Tho University by Do Thuy Huong ([ORCID 0000-0002-7711-2487](https://orcid.org/0000-0002-7711-2487)) and Phan Anh Tu ([ORCID 0000-0003-0667-3137](https://orcid.org/0000-0003-0667-3137)).  
Purpose-built for international-business meta-analysis: semi-automated effect-size extraction from academic PDFs with human-in-the-loop PI verification and immutable data lock.

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21282516.svg)](https://doi.org/10.5281/zenodo.21282516)
![version](https://img.shields.io/badge/version-7.1.1-blue) ![python](https://img.shields.io/badge/python-FastAPI-green) ![frontend](https://img.shields.io/badge/frontend-React%2018%20%2B%20TS-61dafb) ![license](https://img.shields.io/badge/license-Academic%20Source--Available-lightgrey)

## System Architecture

```text
frontend (React 18, :3000)
    └── calls ──→ backend (FastAPI, :8765)
                     ├── extractor.py   provider-configurable LLM parsing
                     ├── notion_sync.py Notion database sync
                     └── models.py      Pydantic domain models
```

## Quick Start

```bash
# 1. Configure environment
cp backend/.env.example backend/.env
# Edit backend/.env: LLM_API_KEY, LLM_MODEL, NOTION_TOKEN, NOTION_DATABASE_ID
# Backward-compatible provider-specific environment variables are also supported.

# 2. Start with Docker Compose
docker compose up

# 3. Open browser
open http://localhost:3000
```

## Development & tests

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

CI runs the backend test suite and the frontend Vite build on every change
(`.github/workflows/maida-ci.yml`). The frontend was migrated from the
deprecated Create-React-App (`react-scripts`) to **Vite** so it builds cleanly
under React 19. Set `VITE_API_URL` (see `frontend/.env.example`) to point the
client at a non-default backend URL.

## API Routes

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/extract` | Base64 PDF body to extracted effect size |
| POST | `/api/extract/upload` | Multipart PDF upload to extracted effect size |
| GET | `/api/studies` | List studies (filter: icrv, dpl, verified, locked) |
| GET | `/api/studies/{id}` | Single study detail |
| PATCH | `/api/studies/{id}/verify` | PI field overrides + approval |
| POST | `/api/studies/{id}/lock` | Irreversible PI data lock |
| GET | `/api/studies/export/csv` | Export locked studies as CSV |
| POST | `/api/notion/sync` | Push locked studies to Notion |
| GET | `/api/health` | Health check + service configuration flags |

## Extraction Workflow

1. **Parse**: PDF text extracted via MuPDF, segmented into statistical regions.
2. **Identify**: a configurable LLM-provider adapter proposes the focal I-P coefficient (not interactions/controls); moderators ICRV/DPL/cDAI are left blank for PI assignment from lookup tables.
3. **Convert**: hierarchy: direct *r* to *r* from *t* to *r*_partial from beta (Peterson & Brown, 2005).
4. **Verify**: PI reviews each field; confidence < 0.70 is mandatory review.
5. **Lock**: PI data lock is cryptographically timestamped and irreversible.

## Citation

If you use M-AIDA, please cite it (see `CITATION.cff`: GitHub renders a
"Cite this repository" button):

> Do, T. H., & Phan, A. T. (2026). *M-AIDA: Meta-Analysis Intelligent Data Assistant* (Version 7.1.1)
> [Computer software]. Can Tho University. https://doi.org/10.5281/zenodo.21282516

---

## Authorship, license, and research-integrity note

**Authors / copyright:** Do Thuy Huong and Phan Anh Tu, College of Economics, Can Tho University.
M-AIDA was developed by the authors to support effect-size extraction for Paper 6 of the doctoral
dissertation. The source code is published openly on GitHub. A Vietnam Copyright Office (COV)
software-copyright registration is being prepared but has not yet been filed; copyright nonetheless
subsists automatically under Vietnamese law and the Berne Convention from the moment of creation.

**Role of computational assistance:** M-AIDA uses a configurable large-language-model provider only to
*propose* candidate effect sizes and statistical conversions from study text. It is a
**human-in-the-loop** tool: every proposed value must be independently verified, corrected if needed,
and permanently locked by the Principal Investigator (`pi_locked`) before it enters the analysis
database. The provider does not select studies, decide eligibility, run the meta-analysis, write
interpretive content, or hold authorship/ownership over the software. Scientific responsibility remains
with the named human authors.

**Security:** copy `backend/.env.example` to `backend/.env` and supply your own keys; never commit a
real `.env` (it is git-ignored).

> Schema note (v7.0.1, 2026-06-10): the tool schema is aligned with the canonical P6 analysis
> database: ICRV = Institutional Context Regime Variation (I/II/III/FR/MX, WGI Rule of Law);
> cDAI = country Digital Adoption Index (0-1). ICRV, DPL, and cDAI are **PI-assigned from external
> lookup tables during verification**; the LLM extracts only statistics, the data-year window, and
> the two text-determinable classifications (DOI measure, performance measure).

## License

Academic Source-Available License: see `LICENSE`. The software is public for
transparency, citation, and academic verification; all rights are reserved by the
authors under automatic copyright.
