# Runbook

Operational notes for running lutz-bot on a VPS. Code documents *what*; this doc captures the *how* and *why* of the surrounding infra.

## Database

Production uses Postgres (locally on the VPS). SQLite is only used by the test suite (in-memory) for fast, ephemeral runs.

### One-time provisioning

```bash
# As the postgres superuser
sudo -u postgres psql <<'SQL'
CREATE ROLE lutz_bot WITH LOGIN PASSWORD '<generate-with-secrets.token_urlsafe>';
CREATE DATABASE lutz_bot OWNER lutz_bot;
GRANT ALL PRIVILEGES ON DATABASE lutz_bot TO lutz_bot;
SQL
```

Put the connection string in `backend/.env`:

```
DATABASE_URL=postgresql+asyncpg://lutz_bot:PASSWORD@127.0.0.1:5432/lutz_bot
```

Apply migrations:

```bash
cd backend && uv run alembic upgrade head
```

### Why Postgres, not SQLite

The v1 SQLite database deadlocked under concurrent async writers (scoreboard
/ odds / events / paper-trader loops all sharing one file). The supervisor
failed silently for ~18 days because of it. Postgres handles the concurrency
natively, scales to multi-sport without contention, and is already running
on the VPS.

## Service

```
[Unit]    /etc/systemd/system/kalshi-mrb.service
[Process] uvicorn src.main:app --host 127.0.0.1 --port 8000 --workers 1
[Note]    The data-collection supervisor runs as an asyncio task inside the
          uvicorn lifespan — there is no separate worker process.
```

Common commands:

```bash
systemctl status kalshi-mrb
systemctl restart kalshi-mrb
journalctl -u kalshi-mrb -f
```

## Secrets posture

`.env` and `*.pem` are gitignored. The Kalshi private key currently lives at
`backend/kalshi_private_key.pem` (inside the repo tree but ignored). Moving
it outside the tree (e.g. to `/etc/lutz-bot/`) is a hardening follow-up.

This repo is public — never `git add -f` an ignored secret.
