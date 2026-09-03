"""wechatback — 微信发码后台（FastAPI 入口）.

分层结构：config（配置）/ db（持久化）/ core（业务与安全）/ routes（HTTP 接入）。
管理后台前端：frontend/dist 必须存在（构建产物，Docker 多阶段构建自带）；
缺失时 /admin 返回 503 提示构建，不再提供旧 inline 页面。
对外契约：`uvicorn app:app`。
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse

from db.database import init_db
from routes import api, wechat

app = FastAPI(title="WeChat Redeem Hub")

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
else:

    @app.get("/", include_in_schema=False)
    @app.get("/admin", include_in_schema=False)
    @app.get("/login", include_in_schema=False)
    def frontend_missing():
        return JSONResponse(
            status_code=503,
            content={"detail": "前端未构建，请先执行 npm run build（见 frontend/）"},
        )
