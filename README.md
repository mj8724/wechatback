# wechatback - 微信发码后台

## 说明
- FastAPI 主程序：`app.py`（基于 `app_v2.py`，最新 548行，含防暴力破解）
- 旧版 Flask 备份：`app_flask_legacy.py`（639行，仅参考）
- Docker 部署：`Dockerfile` + `docker-compose.yml`

## 核心功能（已验证线上）
- `GET /wechat` 微信校验 `WECHAT_TOKEN=REDACTED-WECHAT-TOKEN`
- `POST /wechat` 被动回复：`激活码`→发码，`微信群`→810466205，其他→引导
- `GET /admin` 控制台，`GET /api/stats?pwd=`，`POST /api/import`
- DB `/data/wechat_redeem.db` 表 `codes(status,assigned_openid)` + `users(openid,code)` + `messages`（如旧版）

## 本地运行
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000

## Docker
docker build -t wechat-redeem:latest .
docker run -d --name wechat-redeem --restart always -p 8000:8000 -v /opt/wechat-redeem/data:/data wechat-redeem:latest

## 线上路径
- 公网：https://wx.liubaitech.cn (CF Tunnel -> localhost:8000)
- 容器：wechat-redeem @ 1Panel (debian 192.168.31.108)
- 管理：https://wx.liubaitech.cn/admin 密码 REDACTED-PASSWORD / REDACTED-PASSWORD

## SSH
cloudflared access tcp --hostname sshhome.liubaitech.cn --url 127.0.0.1:2222
ssh -p 2222 root@127.0.0.1  # REDACTED-PASSWORD
