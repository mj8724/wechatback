# Roadmap: wechatback

## Overview

单会话完成 `app.py` 单体拆分：路由 / 服务 / DB 分层，保持 `uvicorn app:app` 启动契约与全部线上行为不变，最后用新旧双版对比测试锁定行为一致性。

## Milestones

### Milestone 1: 单体拆分 (M1)
**Target**: `app.py` 548行单体拆分为分层模块，外部契约与回复文案零变化
**Status**: active

**Minimum-phase principle:** 单模块同 concern，按默认 1 phase 执行；内部顺序用 wave 保证（config → db → core → routes → 入口 → 验证）。

#### Phases

- [x] **Phase 1: 分层拆分与行为锁定** — 拆文件 + 新旧对比测试全绿

#### Phase Details

##### Phase 1: 分层拆分与行为锁定
**Goal**: 产出分层代码 + 新旧两版行为一致性证据
**Depends on**: Nothing (first phase)
**Requirements**: REQ-拆分单体文件, REQ-清理Flask残留, REQ-线上行为不变
**Success Criteria** (what must be TRUE):
  1. `uvicorn app:app` 正常启动，`GET /wechat`、`POST /wechat`、`GET /`、`GET /admin`、`GET /api/stats`、`POST /api/import` 全部可用
  2. 新旧两版对同一组请求返回逐字节一致的响应（校验、关键词回复、发码、鉴权、限流）
  3. `app_flask_legacy.py` 未被新代码引用，仅作参考保留

---

## Scope Decisions

- **In scope**: config / db / core(security+wechat) / routes 分层；瘦 `app.py` 入口；对比测试
- **Deferred**: 换数据库、鉴权重写（Out of Scope，见 project.md）
- **Out of scope**: 新功能、多公众号、前端改版

## Roadmap Decisions

| # | Decision | Choice | Source (user / code / default) | Confidence |
|---|----------|--------|-------------------------------|------------|
| 1 | 会话数量 | 1 session（同模块紧耦合，不拆分） | code | high |
| 2 | 分解策略 | direct（单会话，无依赖边） | default | high |
| 3 | 入口兼容 | 保留 `app.py` 文件名与 `app` 对象（uvicorn/Docker 不变） | code | high |
| 4 | 批准方式 | 用户授权全自动完成（auto-approved） | user | high |

## Progress

| Milestone | Phase | Status | Completed |
|-----------|-------|--------|-----------|
| 1. 单体拆分 | 1. 分层拆分与行为锁定 | Completed | 2026-09-03 |
