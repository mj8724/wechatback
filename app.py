"""wechatback — 微信发码后台（FastAPI 入口）.

分层结构：config（配置）/ db（持久化）/ core（业务与安全）/ routes（HTTP 接入）。
管理后台前端：frontend/dist 必须存在（构建产物，Docker 多阶段构建自带）；
缺失时 /admin 返回 503 提示构建，不再提供旧 inline 页面。
对外契约：`uvicorn app:app`。
"""

from pathlib import Path

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, JSONResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

from db.database import init_db
from routes import api, wechat

import config

app = FastAPI(title="WeChat Redeem Hub")

allowed_hosts = [h.strip() for h in os.environ.get("ALLOWED_HOSTS", "*").split(",") if h.strip()] or ["*"]
app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

init_db()

app.include_router(wechat.router)
app.include_router(api.router)

DIST_DIR = Path(__file__).resolve().parent / "frontend" / "dist"
INDEX_FILE = DIST_DIR / "index.html"
if INDEX_FILE.is_file():
    from fastapi.staticfiles import StaticFiles

    app.mount("/assets", StaticFiles(directory=DIST_DIR / "assets"), name="assets")

    @app.get("/", include_in_schema=False)
    @app.get("/admin", include_in_schema=False)
    @app.get("/login", include_in_schema=False)
    def spa():
        return FileResponse(INDEX_FILE)

    @app.get("/{path:path}", include_in_schema=False)
    def spa_fallback(path: str):
        # 仅 HTML 页面请求回退 SPA；API/资源路径保持原状态码
        if path.startswith(("api/", "wechat", "assets/", "healthz", "docs", "openapi.json", "MP_verify_")):
            return JSONResponse(status_code=404, content={"detail": "不存在"})
        return FileResponse(INDEX_FILE)
else:

    @app.get("/", include_in_schema=False)
    @app.get("/admin", include_in_schema=False)
    @app.get("/login", include_in_schema=False)
    def frontend_missing():
        return JSONResponse(
            status_code=503,
            content={"detail": "前端未构建，请先执行 npm run build（见 frontend/）"},
        )
