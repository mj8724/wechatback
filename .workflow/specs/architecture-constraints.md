---
title: "Architecture Constraints"
readMode: required
priority: high
category: arch
keywords:
  - architecture
  - module
  - layer
  - boundary
  - dependency
  - structure
---

# Architecture Constraints

Auto-generated from project structure (spec-setup, 2026-09-03). Update manually as architecture evolves.

## Module Structure
- Type: single-package (flat: `app.py` + `app_flask_legacy.py` at root, no package dirs)
- Key modules:
  - `app.py` — FastAPI 主程序（路由 + 业务 + DB，548行，线上唯一入口）
  - `app_flask_legacy.py` — 旧版 Flask 备份（639行，仅参考，禁止回流逻辑）
  - `Dockerfile` / `docker-compose.yml` — 单容器部署（8000 端口，/data 卷挂载 SQLite）
  - `deploy_cmd.sh` / `rebuild.sh` — 部署与重建脚本

## Layer Boundaries
- 现状：无分层（路由/服务/DB 混在 `app.py`）— Active 目标即拆分为 routes / services / db
- 拆分约束：`GET /wechat`、`POST /wechat`、`GET /admin`、`GET /api/stats`、`POST /api/import` 对外契约冻结
- DB 边界：所有 SQL 必须收敛到 db 层；路由层禁止直连 sqlite3

## Dependency Rules
- `app.py` 仅依赖：stdlib + `fastapi` + `uvicorn[standard]` + `pydantic`（见 requirements.txt）
- 新增依赖需经确认（保持单容器镜像精简）

## Technology Constraints
- Runtime: Python (3.x) + FastAPI + uvicorn
- Module system: flat scripts, no package (`pip install -r requirements.txt`, `uvicorn app:app`)
- Strict mode: no (无 mypy/ruff/pytest 配置；无 tests/ 目录)
- Deploy: 单容器 + SQLite 文件卷（`/data/wechat_redeem.db`），CF Tunnel 对外

## Entries
