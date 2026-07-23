# Deploying M-AIDA (running app)

M-AIDA is a two-service app: a **FastAPI backend** (`backend/`, port 8765) and a
**React/Vite frontend served by nginx** (`frontend/`, port 3000). The frontend's
nginx **proxies `/api/` to the backend**, so on a single host the frontend is the
only service you expose.

> **LLM key is optional for a demo.** Live PDF extraction needs `LLM_API_KEY`;
> without it `/api/extract` returns an explicit `503` and every other feature
> (verify, lock, CSV export, forest data) still works. For a **thesis defense**
> use the offline harness instead — see [`demo/HUONG_DAN_BAO_VE.md`](demo/HUONG_DAN_BAO_VE.md)
> (`python demo/run_defense.py`), which needs no host and no network.

---

## Option A — Single host / VPS (recommended, matches the app design)

Requirements: a Linux host with Docker + Docker Compose.

```bash
git clone https://github.com/thuyhuongctu/M-AIDA.git && cd M-AIDA
cp backend/.env.production.example backend/.env      # fill in LLM_API_KEY etc.
docker compose -f docker-compose.prod.yml up -d --build
# app on http://<host>/   (health: http://<host>/api/health via the proxy)
```

For HTTPS put a TLS reverse proxy in front (one-liner with Caddy):

```bash
# Caddyfile:  your-domain.example { reverse_proxy localhost:80 }
docker run -d --name caddy --network host \
  -v $PWD/Caddyfile:/etc/caddy/Caddyfile caddy
```

Update to a new version: `git pull && docker compose -f docker-compose.prod.yml up -d --build`.

## Option B — Prebuilt images (GHCR)

Tagging a release (`git tag v7.1.x && git push --tags`) runs
[`.github/workflows/deploy-ghcr.yml`](.github/workflows/deploy-ghcr.yml), which
publishes `ghcr.io/<owner>/M-AIDA/maida-backend` and `…/maida-frontend`. A host
can then `docker pull` those images instead of building — point a compose file
at the image tags rather than `build:`.

## Option C — Managed host (Render / Fly.io / Railway)

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
| `NOTION_TOKEN`, `NOTION_DATABASE_ID` | `backend/.env` | optional Notion sync |
| TLS certificate | reverse proxy (Caddy auto-provisions) | HTTPS |

## Production hardening still on the roadmap

The current build stores studies **in memory** (they reset on restart). Before
paid/commercial use, add PostgreSQL persistence, authentication + multi-tenancy,
and billing — see the staged plan in
[`../p6/tools/maida/KE_HOACH_TRIEN_KHAI_APP_vi.md`](KE_HOACH_TRIEN_KHAI_APP_vi.md)
(Part B) in the dissertation repo.
