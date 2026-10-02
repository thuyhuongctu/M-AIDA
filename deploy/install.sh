#!/usr/bin/env bash
# One-shot installer for M-AIDA 8.x on a fresh Ubuntu 22.04/24.04 VPS.
# Run as root (or with sudo):  bash install.sh
# It installs Docker, clones the repository, asks for the configuration file
# and starts the stack. Re-running it updates the checkout and restarts.
set -euo pipefail

REPO="${MAIDA_REPO:-https://github.com/thuyhuongctu/M-AIDA.git}"
BRANCH="${MAIDA_BRANCH:-main}"
DIR="${MAIDA_DIR:-/opt/m-aida}"

if ! command -v docker >/dev/null 2>&1; then
  echo "== Installing Docker"
  apt-get update -y
  apt-get install -y ca-certificates curl git ufw
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  . /etc/os-release
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
fi

echo "== Firewall: allow SSH, HTTP, HTTPS"
ufw allow OpenSSH >/dev/null || true
ufw allow 80/tcp >/dev/null || true
ufw allow 443/tcp >/dev/null || true
ufw --force enable >/dev/null || true

if [ -d "$DIR/.git" ]; then
  echo "== Updating $DIR"
  git -C "$DIR" fetch --all --tags
  git -C "$DIR" checkout "$BRANCH"
  git -C "$DIR" pull --ff-only
else
  echo "== Cloning $REPO ($BRANCH) into $DIR"
  git clone --branch "$BRANCH" "$REPO" "$DIR"
fi

ENV_FILE="$DIR/deploy/.env.cloud"
if [ ! -f "$ENV_FILE" ]; then
  cp "$DIR/deploy/.env.cloud.example" "$ENV_FILE"
  chmod 600 "$ENV_FILE"
  echo
  echo "!! Edit $ENV_FILE now (domain, Supabase URL/key, DATABASE_URL, LLM_API_KEY),"
  echo "   then run this script again to start the stack."
  exit 0
fi

cd "$DIR"
COMPOSE="docker compose -f docker-compose.cloud.yml --env-file deploy/.env.cloud"

echo "== Building the backend image and checking the configuration"
$COMPOSE build backend
if ! $COMPOSE run --rm --no-deps backend python check_cloud.py; then
  echo
  echo "!! The configuration check failed (see the lines marked HONG above)."
  echo "   Fix $ENV_FILE and run this script again. Nothing was started."
  exit 1
fi

echo "== Starting the stack"
$COMPOSE up -d --build
$COMPOSE ps
echo
echo "== Done. Health: https://$(grep -E '^MAIDA_DOMAIN=' deploy/.env.cloud | cut -d= -f2)/api/health"
