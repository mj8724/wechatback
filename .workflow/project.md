# Project: wechatback

## What This Is

微信发码后台：微信公众号被动回复服务，用户发送"激活码"自动发放兑换码，"微信群"返回群微信号。面向公众号运营者，附带 admin 管理后台（发码统计、批量导入）。

## Core Value

微信被动回复发码链路必须稳定可用（校验 → 关键词回复 → 发码/标记已用）。

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

- [x] `GET /wechat` 微信服务器校验（WECHAT_TOKEN）
- [x] `POST /wechat` 被动回复：激活码→发码，微信群→810466205，其他→引导语
- [x] `GET /admin` 管理控制台（密码鉴权 + 防暴力破解限流）
- [x] `GET /api/stats`、`POST /api/import` 发码统计与批量导入
- [x] SQLite 持久化（codes/status/assigned_openid + users + messages）
- [x] Docker 部署（1Panel）+ CF Tunnel 公网接入 https://wx.liubaitech.cn

### Active

<!-- Current scope being built toward. These are hypotheses until shipped. -->

- [ ] 拆分 `app.py` 单体文件（548行）：路由 / 服务 / DB 层分离
- [ ] 清理 Flask 残留（`app_flask_legacy.py` 仅参考，逻辑以 FastAPI 为准）
- [ ] 重构过程保持线上行为不变（校验、回复文案、发码语义、鉴权）

### Out of Scope

<!-- Explicit boundaries. Include reasoning to prevent re-adding. -->

- 换数据库（SQLite → MySQL/Postgres）— 当前单机发码量足够，暂无并发/备份痛点
- 整体重写发码逻辑与鉴权体系 — 先做结构拆分，不碰业务语义

## Context

- 主程序 `app.py`（FastAPI，548行，含防暴力破解）；旧版 Flask 备份 `app_flask_legacy.py`（639行，仅参考）。
- 线上：容器 wechat-redeem @ 1Panel（debian 192.168.31.108），CF Tunnel → localhost:8000。
- DB 路径 `/data/wechat_redeem.db`（compose 挂载 /opt/wechat-redeem/data）。
- 已做 codebase mapping（kg index：38 nodes）。

## Constraints

- **兼容**: 重构不得改变线上微信接口行为 — 回复文案与发码语义冻结
- **安全**: admin 密码与 TOKEN 经环境变量注入，不落代码
- **部署**: 保持 Dockerfile + docker-compose.yml 单容器部署形态

## Tech Stack

- **Language**: Python
- **Framework**: FastAPI + uvicorn
- **Database**: SQLite (sqlite3)

## Key Decisions

<!-- Decisions that constrain future work. Add throughout project lifecycle. -->

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 首要目标=拆分单体文件而非换库/重写 | 用户确认：结构拆分，业务语义冻结 | — Pending |
| research/reflection/commit/auto-sync 全开 | 初始化偏好问答 | — Pending |

## Stakeholders

- 公众号运营者（发码管理后台使用者）

---
*Last updated: 2026-09-03 after initialization*
