"""wechatback — 微信发码后台（FastAPI 入口）.

分层结构：config（配置）/ db（持久化）/ core（业务与安全）/ routes（HTTP 接入）。
管理后台前端：frontend/dist 存在时托管 Vue SPA（/、/admin、/login），
否则回退到旧 inline 页面（routes.admin），保证不构建也能跑。
对外契约保持不变：`uvicorn app:app`。
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from db.database import init_db
from routes import admin, api, wechat

app = FastAPI(title="WeChat Redeem Hub")

init_db()

app.include_router(wechat.router)
app.include_router(api.router)

DIST_DIR = Path(__file__).resolve().parent / "frontend" / "dist"
if DIST_DIR.joinpath("index.html").is_file():
    from fastapi.staticfiles import StaticFiles

    app.mount("/assets", StaticFiles(directory=DIST_DIR / "assets"), name="assets")

    @app.get("/", include_in_schema=False)
    @app.get("/admin", include_in_schema=False)
    @app.get("/login", include_in_schema=False)
    def spa():
        return FileResponse(DIST_DIR / "index.html")
else:
    app.include_router(admin.router)
