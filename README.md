# wechatback - 微信发码后台

## 说明
- FastAPI 分层应用：`app.py` 入口 + `config/` `db/` `core/` `routes/`（旧单体已拆分）
- 旧版 Flask 备份：`app_flask_legacy.py`（仅参考）
- 前端：`frontend/`（Vue 3 + Vite + Tailwind，构建产物 `frontend/dist` 由 FastAPI 托管）
- Docker 部署：多阶段 `Dockerfile` + `docker-compose.yml`

## 核心功能
- `GET /wechat` 微信校验；`POST /wechat` 被动回复（验签名 + 时间窗口 + 节流）：`激活码`→发码，`微信群`→810466205，其他→引导
- `GET /admin` 控制台（Vue SPA，独立 `/login` 登录页，Bearer token 鉴权）
- 管理 API（均需 `Authorization: Bearer <token>`，`POST /api/login {pwd}` 获取）：
  `GET /api/stats`、`GET /api/users`、`POST /api/import`（去重识别）、
  `POST /api/codes/reset`、`POST /api/codes/delete`、`POST /api/codes/delete-unused`、
  `POST /api/users/reset`、`POST /api/users/reset-batch`
- DB `/data/wechat_redeem.db` 表 `codes` + `users` + `messages` + `admin_tokens`

## 环境变量（必需，见 `.env.example`）
```bash
cp .env.example .env   # 填写后启动，无 WECHAT_TOKEN / ADMIN_PASSWORD 拒绝启动
```
- `WECHAT_TOKEN`：须与微信公众平台配置一致
- `ADMIN_PASSWORD`：管理密码（逗号分隔可配多个），只存 `.env`（不进仓库）
- `DB_PATH`：默认 `/data/wechat_redeem.db`，本地可用 `./data/wechat_redeem.db`

## 本地运行
```bash
pip install -r requirements.txt
cd frontend && npm install && npm run build && cd ..
set -a; source .env; set +a
uvicorn app:app --host 0.0.0.0 --port 8000
```

## Docker
```bash
docker build -t wechat-redeem:latest .
docker run -d --name wechat-redeem --restart always -p 8000:8000 \
  -v /opt/wechat-redeem/data:/data --env-file .env wechat-redeem:latest
```
或 `docker compose up -d --build`（compose 从 `.env` 读取密钥）。

## 线上路径
- 公网：https://wx.liubaitech.cn (CF Tunnel -> localhost:8000)
- 容器：wechat-redeem @ 1Panel (debian 192.168.31.108)
- 管理：https://wx.liubaitech.cn/admin（密码见服务器 `.env`，已轮换，旧密码失效）
- 部署注意：`.env` 须同步到服务器（`/opt/wechat-redeem/.env`），仅透过 CF Tunnel 对外，不要直接暴露 8000

## SSH
cloudflared access tcp --hostname sshhome.liubaitech.cn --url 127.0.0.1:2222
ssh -p 2222 root@127.0.0.1
