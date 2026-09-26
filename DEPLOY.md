# Deploying M-AIDA (running app)

M-AIDA is a two-service app: a **FastAPI backend** (`backend/`, port 8765) and a
**React/Vite frontend served by nginx** (`frontend/`, port 3000). The frontend's
nginx **proxies `/api/` to the backend**, so on a single host the frontend is the
only service you expose.

> **LLM key is optional for a demo.** Live PDF extraction needs `LLM_API_KEY`;
> without it `/api/extract` returns an explicit `503` and every other feature
> (verify, lock, CSV export, forest data) still works. For a **thesis defense**
> use the offline harness instead: see [`demo/HUONG_DAN_BAO_VE.md`](demo/HUONG_DAN_BAO_VE.md)
> (`python demo/run_defense.py`), which needs no host and no network.
>
> **Real extraction on your own Windows PC, no server:** double-click
> `CHAY_MAIDA_WINDOWS.bat`; see [`demo/HUONG_DAN_CHAY_THAT.md`](demo/HUONG_DAN_CHAY_THAT.md).

---

## Option A: Single host / VPS (recommended, matches the app design)

Requirements: a Linux host with Docker + Docker Compose.

```bash
git clone https://github.com/thuyhuongctu/M-AIDA.git && cd M-AIDA
cp backend/.env.production.example backend/.env      # fill in LLM_API_KEY etc.
python3 -c "import secrets; print(secrets.token_urlsafe(32))"   # -> MAIDA_ADMIN_KEY
docker compose -f docker-compose.prod.yml up -d --build
# app on http://<host>/   (health: http://<host>/api/health via the proxy)
```

> **Set `MAIDA_ADMIN_KEY` before going live.** nginx proxies every `/api/`
> request to the backend, verify/lock/extract/Notion-sync included, so
> without this key any site visitor could edit or lock studies. Left unset,
> the backend still starts (a fresh key is generated and printed to the
> container log on every restart) so a quick local check never breaks, but a
> real deployment needs the key set explicitly to stay stable across
> restarts and to actually keep visitors out.

For HTTPS put a TLS reverse proxy in front (one-liner with Caddy):

```bash
# Caddyfile:  your-domain.example { reverse_proxy localhost:80 }
docker run -d --name caddy --network host \
  -v $PWD/Caddyfile:/etc/caddy/Caddyfile caddy
```

Update to a new version: `git pull && docker compose -f docker-compose.prod.yml up -d --build`.

## Option B: Prebuilt images (GHCR)

Tagging a release (`git tag v7.1.x && git push --tags`) runs
[`.github/workflows/deploy-ghcr.yml`](.github/workflows/deploy-ghcr.yml), which
publishes `ghcr.io/<owner>/M-AIDA/maida-backend` and `…/maida-frontend`. A host
can then `docker pull` those images instead of building, point a compose file
at the image tags rather than `build:`.

## Option C: Managed host (Render / Fly.io / Railway)

Deploy the two Dockerfiles as two services and set the LLM secrets in the host
dashboard. Because the services are then on **separate origins**, build the
frontend with an absolute backend URL and open CORS on the backend:

```
# frontend build arg
VITE_API_URL=https://api.your-domain.example
# backend env
CORS_ORIGINS=https://your-frontend-domain.example
```

On hosts that inject their own `$PORT`, override the backend start command to
`uvicorn main:app --host 0.0.0.0 --port $PORT`.

---

## Secrets checklist (set on the host, never in git)

| Secret | Where | Needed for |
|---|---|---|
| `LLM_API_KEY` (+ `LLM_PROVIDER`, `LLM_MODEL`) | `backend/.env` / host secret | live PDF extraction |
| `MAIDA_ADMIN_KEY` | `backend/.env` / host secret | blocks visitors from editing/locking studies (see above) |
| `NOTION_TOKEN`, `NOTION_DATABASE_ID` | `backend/.env` | optional Notion sync |
| TLS certificate | reverse proxy (Caddy auto-provisions) | HTTPS |

## Runtime configuration (not secret)

| Variable | Default | Meaning |
|---|---|---|
| `MAIDA_DB_PATH` | `maida.db` | SQLite file backing the study store. Point it at a mounted volume in containers; `docker-compose.yml` already maps `/data`. |
| `MAIDA_DEMO_MODE` | `false` | Presentation-only: reported via `/api/health`, and stands down the `MAIDA_ADMIN_KEY` guard because `demo/run_defense.py` already protects every mutation with its own presenter PIN. **Keep this off wherever real research data lives** - it is not a general-purpose way to disable the admin key. |

## Production hardening still on the roadmap

Studies are now persisted in SQLite, so they survive a process restart, and a
`MAIDA_ADMIN_KEY` (above) keeps an anonymous visitor from editing or locking
them - sufficient for single-researcher and demo use but not for
multi-tenant service, where different users need different access rather
than one shared secret. Before paid/commercial use, add PostgreSQL
persistence, per-user authentication + multi-tenancy, upload limits with
server-side type checking, and billing, see the staged plan in
[`../p6/tools/maida/KE_HOACH_TRIEN_KHAI_APP_vi.md`](KE_HOACH_TRIEN_KHAI_APP_vi.md)
(Part B) in the dissertation repo.
