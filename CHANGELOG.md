# Changelog: M-AIDA (Meta-Analysis Intelligent Data Assistant)

All notable changes to this project are documented here. Versions follow the
internal release line used during the doctoral meta-analysis (P6).

## 7.1.2 (chưa phát hành, chờ tác giả duyệt)

Bản vá quản trị: đưa mã về đúng với giao thức đã mô tả trong tài liệu,
không thay đổi kết quả của các bản ghi P6 đã khóa.

- Chặn phòng vệ r trong [-1, 1] cho mọi tuyến chuyển đổi (t bị chặn sẵn
  theo công thức; beta và ghi đè r trực tiếp nay được chặn tường minh).
- Gắn cờ bắt buộc kiểm chứng khi |beta| > 0,5, ngoài miền dẫn xuất của
  Peterson & Brown (2005).
- Thực thi quy tắc df = n - 2 khi df không được báo cáo, kèm cờ
  `df_imputed` minh bạch.
- Lưu `machine_proposal`: ảnh chụp bất biến các giá trị máy đề xuất tại
  thời điểm trích xuất, không thể ghi đè, tách bạch máy đề xuất với
  con người quyết định ở cấp từng bản ghi.
- 10 unit test mới, gồm test API xác nhận bản ghi đã khóa trả 409.

## [Unreleased]
- Web: unified public web app (overview, method, positioning, forest plot,
  interactive study atlas, in-browser demo tool) served via GitHub Pages at
  https://thuyhuongctu.github.io/M-AIDA/ from the repository root and `docs/`.

## [7.1.1] - 2026-07-09
- Documentation: revised public-facing wording to describe the extraction layer
  as a configurable LLM-provider adapter rather than a contribution from any
  external model/vendor.
- Configuration: added provider-neutral `LLM_PROVIDER`, `LLM_API_KEY`, and
  `LLM_MODEL` environment variables while retaining backward-compatible aliases
  for existing local deployments.
- Repository hygiene: removed the legacy standalone webapp artifact that used a
  direct model-specific API call and model-specific audit wording. The maintained
  application remains under `backend/` and `frontend/`.

## [7.1.0] - 2026-07-09
- Packaging: added `backend/pyproject.toml` (PEP 621) making the backend
  pip-installable (`pip install -e backend[test]`), with pinned runtime
  dependencies and a `test` extra.
- Tests: added `backend/tests/` (pytest) pinning the Cohen (1988) t→r and
  Peterson & Brown (2005) β→r conversions, sign preservation, the unit-interval
  bound, and the three-level confidence scheme / PI-review threshold.
- Frontend: migrated from the deprecated Create-React-App (`react-scripts` 5,
  which cannot build under React 19) to **Vite 6** + `@vitejs/plugin-react`.
  Added `vite.config.ts`, root `index.html`, `tsconfig.json`, `src/vite-env.d.ts`,
  and `frontend/.env.example`; the API base URL now reads `import.meta.env.VITE_API_URL`.
  Build output stays in `build/` so the Docker/nginx setup is unchanged.
- CI: added `.github/workflows/maida-ci.yml` running the backend pytest suite
  and the frontend Vite production build on every change.

## [7.0.1] - 2026-06-10
- Schema alignment with the P6 analysis database: `cdai_score` relabelled to
  country Digital Adoption Index (0-1); ICRV enum corrected to the
  institutional I/II/III/FR/MX taxonomy; DOI-type and performance-type enums
  aligned to the coded study database.
- ICRV regime, DPL phase, and cDAI moved to PI-assigned fields (the LLM no
  longer codes them); extraction limited to statistical quantities.
- Model ID made configurable through the project settings layer.

## [7.0.0] - 2026-06-08
- Two-tab workflow finalised: **Extract** (LLM PDF to effect sizes) and
  **Verify & Lock** (PI dashboard, overrides, immutable lock).
- Pydantic v2 domain models: `ExtractedEffect`, `StudyDatabaseEntry`,
  `VerificationDecision`.
- Notion two-way sync (`notion_sync.py`) for the coded study database.
- CSV export restricted to `pi_locked=True` records to `forest_data.csv`,
  the analysis input for the three-level meta-analysis (k=238, K=288).
- Dockerised (backend FastAPI :8765, frontend React :3000).

## Earlier (internal, pre-release)
- v6.x: extraction-hierarchy conversion (t/F/β to Pearson r) hardening.
- v5.x: verification dashboard and override/adjudication logic.
- v1-v4: prototype PDF text extraction (PyMuPDF) and LLM prompt iterations.

> Version history reflects iterative, human-directed development; see the git
> commit log for the full, dated trail.

## Governance note - 2026-07-13

- **[7.1.1] is declared the Registered Reference Release (frozen).** This is
  the version deposited in the copyright-registration dossier filed through
  Can Tho University and the version used in the dissertation (P6). No direct
  changes may be made to the 7.1.1 source, architecture, features, or UI; see
  `IP_REGISTER.md` for the full post-freeze rules and the 7.1.0/7.1.1
  reconciliation note.
- **Semantic Versioning rules from this point on:**
  - `7.1.2+` (patch): bug fixes only; no new features, no architecture change.
  - `7.2.0` (minor): new features that keep the current architecture and
    purpose ("Meta-Analysis Intelligent Data Assistant"); developed on a
    separate branch, never on the 7.1.1 release.
  - `8.0.0` (major): substantial changes to architecture or scope.
- Supplementary IP registration for any later version is considered only when
  that version contains significant creative changes, and only after
  consulting an intellectual-property specialist.
