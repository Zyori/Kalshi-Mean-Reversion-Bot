# Archive

Frozen snapshots of prior project state. Not tracked in git (see `.gitignore`); kept on the VPS for local-only forensic reference.

| File | Size | Notes |
|------|------|-------|
| `bot-v1-sqlite-2026-04-25-final.db.gz` | ~37 MB | Final SQLite database from v1. Collection stalled on 2026-04-25 due to persistent `database is locked` errors in the async supervisor. Compressed snapshot captured 2026-05-12 just before the Postgres migration and clean-slate wipe. Contains 174 games across 6 sports and accompanying events/lines; no paper-trade history of analytical value retained. |

If you ever need to inspect v1 data:

```bash
gunzip -k docs/archive/bot-v1-sqlite-2026-04-25-final.db.gz
sqlite3 docs/archive/bot-v1-sqlite-2026-04-25-final.db ".tables"
```
