# M-AIDA: Meta-Analysis Intelligent Data Assistant

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21282516.svg)](https://doi.org/10.5281/zenodo.21282516)
![version](https://img.shields.io/badge/version-7.2.1-blue) ![python](https://img.shields.io/badge/python-FastAPI-green) ![frontend](https://img.shields.io/badge/frontend-React%2019%20%2B%20TS-61dafb) ![license](https://img.shields.io/badge/license-AGPL--3.0-blue)

Research software for meta-analysis: semi-automated effect-size extraction from
academic PDFs with a vendor-neutral large-language-model adapter, human-in-the-loop
verification by the principal investigator, and an immutable data-lock workflow that
exports a reproducible effect-size dataset for three-level meta-analytic regression.

**Authors**

- Do Thuy Huong ([ORCID 0000-0002-7711-2487](https://orcid.org/0000-0002-7711-2487)), PhD Candidate, School of Economics, Can Tho University.
- Phan Anh Tu ([ORCID 0000-0003-0667-3137](https://orcid.org/0000-0003-0667-3137)), School of Economics, Can Tho University.

Built to support the P6 (meta-analysis) component of the first author's doctoral
dissertation on the internationalization-performance relationship.

**Scope: which kinds of literature review this serves.** M-AIDA is an
extraction-and-verification engine at the data-collection stage of PRISMA; it
does not search the literature, does not screen records, and does not run the
final statistical model. It serves a **meta-analysis** in full (its design
target), the **data-extraction stage of a systematic review** (evidence-gated
coding, recorded exclusion reasons, two independent coders), and **small-scale
evidence tables** that ground the hypotheses of a proposal. It is of partial
use for scoping reviews, marginal use for narrative reviews, and no use for
bibliometric analysis, which is a different class of tool.

## System Architecture

```text
frontend (React 19, :3000)
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
# Windows one-click alternative: demo\\start_defense_windows.bat
# macOS/Linux alternative: sh demo/start_defense_unix.sh
# open http://localhost:8765/  (interactive API docs at /docs)
```

Seeding rules and options (full-database seed, lock-all mode) are documented in
`demo/run_defense.py`; a Vietnamese walkthrough for the defense session is in
`demo/HUONG_DAN_BAO_VE.md`. The Defense App persists session changes locally, protects all mutations with a
presenter PIN printed at startup, and can reset to the verified P6 seed. Live PDF
extraction additionally requires `LLM_API_KEY` in `backend/.env`; without it the
extraction endpoint returns an explicit 503 and verification, locking, filtering,
reset, and CSV export continue to work offline.

## Production deployment

To run the app for real (single host / VPS, prebuilt GHCR images, or a managed
host) see **[DEPLOY.md](DEPLOY.md)**: `docker-compose.prod.yml`,
`backend/.env.production.example`, and a GHCR image-build workflow are provided.
The staged plan toward a commercial SaaS (PostgreSQL, auth, billing) is in
`KE_HOACH_TRIEN_KHAI_APP_vi.md` in the dissertation repository.

## Development and tests

```bash
# Backend unit tests (effect-size conversions + confidence scheme)
cd backend
pip install -e ".[test]"
pytest -q

# Independent-validation analysis tests (synthetic fixtures only)
cd ..
python -m pytest -q validation/tests

# Frontend (Vite): dev server / production build
cd frontend
npm ci
npm run dev      # http://localhost:3000
npm run build    # outputs to build/
```

CI runs the backend test suite and the frontend Vite build on every change.
Set `VITE_API_URL` (see `frontend/.env.example`) to point the client at a
non-default backend URL.

The executable independent-validation package is in [`validation/`](validation/),
with the preregister-before-running design in
[`VALIDATION_PROTOCOL.md`](VALIDATION_PROTOCOL.md). Its templates separate two
human coders, the adjudicated gold standard, untouched machine proposals, and
PI verification time. No product-accuracy claim is made until real frozen
inputs and generated results are archived; synthetic CI fixtures only verify
the metric calculations.

Execution status: the repository now includes a deterministic provisional
sampling frame of 40 PRIMARY studies plus 10 RESERVE studies in
[`validation/sampling/`](validation/sampling/). Defense-demo studies and every
study flagged `is_estimated` in the P6 database are excluded. The frame is not
locked until full-text availability and non-use in M-AIDA development are
confirmed for every PRIMARY study; the freeze command enforces both gates.

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
   At most 40,000 characters of text are sent to the model (`PDF_TEXT_LIMIT`); when a
   paper is longer the record carries `text_truncated = true`, so an empty proposal
   can be told apart from a paper that reports no statistic.
2. **Identify**: the LLM adapter proposes the focal internationalization-performance
   coefficient (not interactions or controls). Moderators (ICRV, DPL, cDAI) are left
   blank for the principal investigator to assign from external lookup tables.
3. **Convert**: the canonical target is Pearson r. When only a derived statistic is
   reported, r is computed from t using Cohen (1988) with df = n − p − 1 taken from
   the model's predictor count, or from a standardized beta using Peterson and
   Brown (2005): full formula r = 0.98β + 0.05λ, valid only for |β| ≤ 0.5;
   out-of-domain betas are rejected, never approximated. Each record carries
   `metric_type`, `estimand_source`, and `source_controls`, so beta-derived values
   enter sensitivity analysis only, and a three-level confidence score is attached.
4. **Evidence gate**: a record is created only with page-and-quote evidence for
   **both** the statistic and the sample size (`evidence_page`/`evidence_quote`,
   `n_evidence_page`/`n_evidence_quote`). Missing evidence raises HTTP 422 and no
   record is stored: the system has no default or fallback output path for any
   input.
5. **Verify**: the principal investigator reviews each field; any record with
   confidence below 0.70 is flagged for mandatory review. Corrections go through a
   whitelist of PI-editable fields (`PI_EDITABLE_FIELDS`, 7.2.0); a change to any
   primary statistic re-derives r, the variances (`variance_r`, `variance_z`),
   `metric_type` and the provenance fields through the same function live
   extraction uses. The machine's proposal, its confidence score and the evidence
   quotes are never editable; human edits are logged in `pi_edited_fields`.
6. **Lock**: an approved record that carries an effect size and its variance is
   permanently locked with a UTC timestamp and can no longer be edited; `pi_locked`
   and `locked_at` cannot be set by any other route. Only locked records enter the
   analysis export, which carries every field of the record.

## Effect-size recoding and lock generations (`analysis/`)

The [`analysis/`](analysis/) package is the canonical, self-tested implementation
of the conversion layer (`effect_size.py` with hand-computed unit tests, plus an
R twin `effect_size.R` feeding the metafor pipeline). `migrate_v8.py` derives a
new lock generation from a released dataset without ever editing it: v7.1.1
(DOI-pinned) stays immutable, every derived record carries a `derived_from`
pointer, and excluded records keep a written reason (PRISMA-ready). Each run
emits `figures.json`: the single source every display surface reads its
headline numbers from. Policy details are in
[`analysis/README.md`](analysis/README.md).

## Live web pages (GitHub Pages)

The repository is also served as a static site (GitHub Pages):

- **Main page** ([index.html](https://thuyhuongctu.github.io/M-AIDA/)): overview,
  positioning, the interactive atlas of the locked study corpus, the in-browser
  extraction console (three sample papers: r, t, standardized beta, walked
  through the same convert/verify/lock/export gates; it refuses PDFs, which need
  the backend), and the Huong AI tour guide. Bilingual EN/VI.
- **Defense App** ([defense.html](https://thuyhuongctu.github.io/M-AIDA/defense.html)):
  public explanation of the presenter-controlled local application, its
  Academic Demo / Defense App / Cloud boundaries, rehearsal flow, and launch
  instructions. Verify, Lock, and Reset remain local rather than public.
- **Commercial page** ([commercial.html](https://thuyhuongctu.github.io/M-AIDA/commercial.html)):
  productization and licensing overview.
- **Data & Melody** ([data_melody.html](https://thuyhuongctu.github.io/M-AIDA/data_melody.html)):
  the story of the software told as a guided walk with Huong AI (Vietnamese,
  English, French), with a live World Bank indicators widget.
- **Creative Library** ([library.html](https://thuyhuongctu.github.io/M-AIDA/library.html)):
  a hub that links the project's components (the meta-analysis platform, the
  Data & Melody walk, the songs, the BizOn simulation game, and the academic
  page), with a Huong AI image gallery. Bilingual EN/VI with light/dark themes.
- **Songs** ([songs.html](https://thuyhuongctu.github.io/M-AIDA/songs.html)):
  the main work *"The Heartbeat of M-AIDA (Que les preuves decident)"* on an
  immersive 3D lyric console with synchronized lyrics, an artist gallery, and a
  curated pair of non-duplicate recordings (the extended main work plus
  *"Je m'appelle Hương – mon histoire"*).
- **BizOn AI** ([bizon.html](https://thuyhuongctu.github.io/M-AIDA/bizon.html)):
  a playable, multi-agent "living market" business-simulation game used in the
  author's Business Simulation course.
- **Author's academic homepage** ([huong.html](https://thuyhuongctu.github.io/M-AIDA/huong.html)):
  Do Thuy Huong's personal page, bio, publications (ORCID), teaching linked to
  research, journal peer-review / academic service, an interactive 3D globe of the
  studied economies, a World Bank data widget, and a blog. Bilingual VI/EN with
  light/dark themes.
- **Privacy policy** ([privacy.html](https://thuyhuongctu.github.io/M-AIDA/privacy.html)):
  cookieless-analytics disclosure (VI/EN).

**Theme song.** The project's main work is *"The Heartbeat of M-AIDA (Que les
preuves decident)"* (`assets/maida_song_official.mp3`, an extended cut of about
4.5 minutes). It is featured on the Songs page and is available site-wide
through a shared floating player that loops the curated pair (the main work plus
*"Je m'appelle Hương – mon histoire"*). The mood menu on the main and commercial
pages plays the *heartbeat* recording (`assets/maida_song_heartbeat.mp3`), with an
instrumental option. All lyrics were written by Do Thuy Huong (17 July 2026). The
Data & Melody page carries the full song cover: the author's ao dai portrait on a
floral backdrop with animated falling music notes and a Vietnam map watermark.

**Design.** The main and commercial pages ship a premium editorial design in the
*"Je m'appelle Hương"* brand palette: a warm ivory default theme with a
dusty-mauve primary and a warm-gold accent, a rosewood dark theme behind the
toggle, glass cards, scroll-reveal animations, and a scroll progress bar. The
academic `asia-*` atlas pages keep their own terracotta/ochre/green data theme. All character artwork
uses the realistic 3D Huong character in high resolution; cross-page links
carry the selected language (`?lang=`), and Data & Melody opens in French by
default with VI / EN / FR toggles.

**Brand and design system.** The official brand kit lives in
[`assets/brand/`](assets/brand/) (diamond mark, lockups, favicon, og-image, and
usage rules including the two-design-system boundary with the institutional
identity); the page headers render the official mark bound to theme tokens.
Design tokens and components are canonical in [`css/tokens.css`](css/tokens.css)
and [`css/components.css`](css/components.css), documented in
[`styleguide.html`](styleguide.html) (plus a fully offline
`styleguide-standalone.html`). Fonts are self-hosted woff2 subsets
([`assets/fonts/`](assets/fonts/), SIL OFL: see `THIRD_PARTY_LICENSES.md`);
no external font CDN is called.

**Data consistency.** Every headline research number on the site (studies,
effect sizes, economies, pooled and bias-adjusted *r*, I²) has a single source
of truth in [`assets/data/site-metrics.json`](assets/data/site-metrics.json),
mirrored from the locked P6 corpus (`p6/results/table1_baseline.csv` in the
dissertation repo). A guard, [`scripts/check_site_metrics.py`](scripts/check_site_metrics.py),
runs in the GitHub Pages workflow and **fails the deploy** if any page drifts
from those numbers, so the published pages cannot show stale statistics.

The narration layer follows the same discipline from the other side: the Huong
AI voice guide never speaks a research number. She explains the process; the
numbers stay on screen, read from the single source. Recordings therefore never
go stale when the dataset moves to a new lock generation.

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

M-AIDA is free/open-source software under the **GNU Affero General Public License
v3.0 (AGPL-3.0-only)**, see [`LICENSE`](LICENSE). The AGPL's Section 13 covers
network use: running a modified version as a service requires publishing that
version's source.

Using M-AIDA under the AGPL requires no contact and no fee.

**Commercial licensing is not currently available.** Granting terms other than
the AGPL requires holding, or being authorised by all co-holders to grant, the
economic rights in the work. Those rights are not yet formally settled (see the
next section), so no such grant can be made today. The position is stated in
full in [`COMMERCIAL-LICENSE.md`](COMMERCIAL-LICENSE.md).

AGPL-3.0-only supersedes the earlier "M-AIDA Academic Source-Available License
v1.0", retired on 4 August 2026. Any document still carrying that name is out of
date; `LICENSE` in this repository is the operative text.

### Ownership, and why the Zenodo files are restricted

Economic rights in M-AIDA are held **jointly by Can Tho University and the two
authors**, under Article 71 of the university's science and technology management
regulation (Decision 5152/QD-DHCT of 6 October 2023). The copyright registration
is filed through the university and is still in process.

Because of that, the archived deposit at
[10.5281/zenodo.21282516](https://doi.org/10.5281/zenodo.21282516) keeps its
**files under restricted access** while the record itself, its metadata and its
DOIs stay public and citable. This does not conflict with the AGPL: the AGPL
governs what a recipient of the software may do with it, and obliges the authors
to supply corresponding source to those recipients. It does not oblige anyone to
publish files in any particular archive. The complete source is public in this
repository, so the AGPL grant is fully effective today.

When the registration completes, opening the deposit is a decision for the joint
owners, not for either author alone.
