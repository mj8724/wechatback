---
title: "Coding Conventions"
readMode: required
priority: high
category: coding
keywords:
  - style
  - naming
  - import
  - pattern
  - convention
  - formatting
---

# Coding Conventions

Auto-generated from project analysis (spec-setup, 2026-09-03). Update manually as patterns evolve.

## Formatting
- Indentation: 4 spaces (Python)
- Line length: not configured (no ruff/black/flake8 config)
- Trailing commas: used in multi-line calls
- Semicolons: N/A (Python)

## Naming
- Variables/functions: snake_case (`get_client_ip`, `record_login_failure`, `assigned_openid`)
- Classes/types: PascalCase (`ImportRequest`, Pydantic models)
- Constants: UPPER_SNAKE_CASE (`DB_PATH`, `WECHAT_TOKEN`, `ADMIN_PASSWORDS`, `MAX_FAILED_ATTEMPTS`)
- Files: snake_case (`app.py`, `app_flask_legacy.py`, `deploy_cmd.sh`, `rebuild.sh`)

## Imports
- Style: stdlib first (`os`, `time`, `hashlib`, `sqlite3`, `xml`), then third-party (`fastapi`, `pydantic`), then `typing`
- Path aliases: none (single-file app, no package)
- Order: built-in, external, internal — no isort config, follow stdlib→third-party→typing order

## Patterns
- Single-file FastAPI app: routes + DB helpers + rate-limit state in one module
- DB access via `get_db()` helper (sqlite3, Row factory); schema created in `init_db()` with `CREATE TABLE IF NOT EXISTS`
- Pydantic models for request bodies (`ImportRequest`); query params inline (`pwd: str = ""`)
- Rate limiting via in-memory `defaultdict` (`login_attempts`) + `HTTPException(429)`
- Client IP resolution prefers `cf-connecting-ip` → `x-real-ip` → `x-forwarded-for` (CF Tunnel deployment)
- Password normalization (`normalize_pwd`) accepts full/half-width variants — preserve when refactoring

## Entries
