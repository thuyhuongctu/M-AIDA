# Publishing M-AIDA: GitHub repository + Zenodo DOI

A step-by-step record of how this source tree became a public, citable,
archived repository: the public evidence of the authors' software-engineering
capability behind the dissertation's meta-analysis (P6).

**Current status (as of v7.1.1):**

- Public repository: <https://github.com/thuyhuongctu-cell/M-AIDA>
- Latest release: **v7.1.1** (from `main`, vendor-neutral build)
- Zenodo archive: concept DOI **[10.5281/zenodo.21282516](https://doi.org/10.5281/zenodo.21282516)** (all versions); version DOI **[10.5281/zenodo.21282517](https://doi.org/10.5281/zenodo.21282517)** (v7.1.1)

## Why a standalone repo

Keep M-AIDA in its **own** public repository, separate from the dissertation
repo. The git commit history (small, dated, explained commits, with bugs found
and fixed) is the strongest provenance evidence that the software was developed
by people over time, not generated in one pass.

## Step 1: repository (done)

The repository is live and public at
<https://github.com/thuyhuongctu-cell/M-AIDA>. `CITATION.cff`
(`repository-code`) points to it. The default branch is `main`; the current
release build is the vendor-neutral tree that resolves the LLM provider
through a configurable Engine Adapter (`LLM_PROVIDER` / `LLM_API_KEY` /
`LLM_MODEL`) rather than any hard-coded model id.

## Step 2: tag and publish the release (done for v7.1.1)

The release is created from `main` so the archived snapshot is the
vendor-neutral build. In the GitHub UI:

1. **Releases** to **Draft a new release**.
2. **Choose a tag** to type `v7.1.1` to **Create new tag: v7.1.1 on publish**,
   Target = `main`.
3. Title "M-AIDA v7.1.1", then **Publish release**.

> Housekeeping: the earlier `v7.1.0` (lowercase) and `V7.1.0` (uppercase)
> tags/releases predate the vendor-neutral build and should be deleted so only
> the clean `v7.1.1` release remains. Delete each on its **Releases** entry,
> then remove any leftover tag on the **Tags** page.

## Step 3: Zenodo permanent DOI (done)

1. Sign in to <https://zenodo.org> **with the GitHub account** that owns the repo.
2. Go to the **GitHub** tab (<https://zenodo.org/account/settings/github/>) and
   toggle the repository **ON**. If it does not appear, click **Sync now**.
3. Publish the `v7.1.1` release (Step 2). Zenodo automatically archives it and
   mints a DOI, reading the record metadata from `.zenodo.json` and
   `CITATION.cff` at the tagged commit (authors, ORCIDs, license, keywords).
4. The minted DOI for v7.1.1 is **10.5281/zenodo.21282517**.

> **Version DOI vs concept DOI.** `10.5281/zenodo.21282517` is the
> **version DOI** for this exact release (v7.1.1). `10.5281/zenodo.21282516`
> is the **concept DOI** ("Cite all versions") that always resolves to the
> newest version. The DOI badge and `CITATION.cff` (primary `doi`) carry the
> **concept DOI** so the "cite this software" reference always points to the
> latest version; the version DOI is retained in `CITATION.cff` `identifiers`
> and in the dissertation's data-availability statements, which pin the exact
> reproducible build used in the analysis.

## Step 4: cite it in the dissertation and papers

- In the front-matter "Danh mục công trình", list the M-AIDA software with its
  Zenodo DOI and, once issued, the Copyright Office of Viet Nam registration
  certificate number.
- In the P6 manuscript's data-availability statement, cite the Zenodo DOI:

  > Do, T. H., & Phan, A. T. (2026). *M-AIDA: Meta-Analysis Intelligent Data
  > Assistant* (Version 7.1.1) [Computer software]. Can Tho University.
  > https://doi.org/10.5281/zenodo.21282517

## Step 5: repository hygiene that signals quality

- [x] `README.md` with architecture, quick start, a "Cite" section, and the DOI badge.
- [x] `CITATION.cff` (GitHub shows a "Cite this repository" button; carries the DOI).
- [x] `LICENSE` (rights preserved + academic use permitted).
- [x] `CHANGELOG.md` (version history).
- [x] `.env.example` committed; real secrets never committed (verify `.gitignore`).
- [ ] A short `demo/` with one sample PDF and the resulting CSV row (optional but
      powerful: a visitor reproduces an extraction end-to-end).

## Anti-AI-suspicion checklist

- Public commit history showing iterative, human-directed development.
- Zenodo DOI + Copyright Office registration (independent authorship attestation).
- `CITATION.cff` linking the software to both authors' ORCIDs.
- Vendor-neutral build: the LLM is a configurable computational tool, never an
  author or owner.
- The authors can open any module (`extractor.py`, `models.py`, `notion_sync.py`)
  and explain it: the decisive provenance check at the defense.
