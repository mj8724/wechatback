"""wechatback — 微信发码后台（FastAPI 入口）.

分层结构：config（配置）/ db（持久化）/ core（业务与安全）/ routes（HTTP 接入）。
对外契约保持不变：`uvicorn app:app`，路由与行为与拆分前一致。
"""

from fastapi import FastAPI

from db.database import init_db
from routes import admin, api, wechat

app = FastAPI(title="WeChat Redeem Hub")

init_db()

app.include_router(wechat.router)
app.include_router(api.router)
app.include_router(admin.router)
