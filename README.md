# wechatback - 微信公众号激活码分发后台

开箱即用的微信公众号被动回复 + 激活码分发系统：用户发关键词领码（一人一码），附带 Vue 管理后台（库存 / 用户 / 留言 / 自定义回复规则）。

## 功能
- 微信被动回复：关键词规则引擎（包含/完全匹配、优先级、启用开关），发码动作一人一码、防超发
- 回复内容全自定义：欢迎语 / 默认回复 / 发码模板 / 重复领取 / 库存告罄，支持 `{code}` `{site}` `{group}` 占位符
- 管理后台（Vue 3 SPA，独立登录页 + 7 天 token）：总览 / 激活码（导入去重、搜索、重置、删除、清空、导出 CSV）/ 用户（按人重置、批量重置）/ 留言（搜索、导出）/ 回复规则
- 安全：签名校验 + 时间窗口、登录限流、IP 节流、Bearer 鉴权、密钥全走环境变量

## 快速开始

```bash
cp .env.example .env   # 填写 WECHAT_TOKEN（须与微信公众平台一致）与 ADMIN_PASSWORD
pip install -r requirements.txt
cd frontend && npm install && npm run build && cd ..
set -a; source .env; set +a
uvicorn app:app --host 0.0.0.0 --port 8000
```

打开 http://127.0.0.1:8000/admin，用 `ADMIN_PASSWORD` 登录。

## 微信公众平台配置
1. 服务器地址填 `https://你的域名/wechat`，令牌填 `WECHAT_TOKEN` 的值
2. 启用后发送关键词即按规则回复；首次使用建议先在后台 💬 回复里改好文案与群微信号

## 配置（环境变量，见 `.env.example`）
| 变量 | 说明 |
|---|---|
| `WECHAT_TOKEN` | 微信校验 Token（必需，与公众平台一致） |
| `ADMIN_PASSWORD` | 管理密码（必需，逗号分隔可配多个） |
| `GROUP_WECHAT_ID` | 群入口微信号（可在后台设置里改） |
| `WEBSITE_URL` | 兑换地址（回复模板 `{site}` 用它） |
| `DB_PATH` | SQLite 路径，默认 `/data/wechat_redeem.db` |
| `TRUST_PROXY_HEADERS` | 置 `1` 才采信 `cf-connecting-ip`（CF Tunnel/反代部署），直连保持 `0` |
| `ALLOWED_HOSTS` | Host 头白名单（逗号分隔），生产填公网域名 |

## Docker 部署
```bash
docker compose up -d --build   # 从 .env 读密钥，数据卷 ./data（compose 可改）
```
生产请置于反向代理（TLS）之后，不要直接暴露 8000；确保数据卷目录对容器用户可写。

## 管理 API（需 `Authorization: Bearer <token>`，`POST /api/login {pwd}` 获取）
- `GET /api/stats`、`GET /api/users`（`q/limit/offset`）、`GET /api/codes`、`GET /api/messages`
- `POST /api/import`（去重）、`POST /api/codes/reset|delete|delete-unused`
- `POST /api/users/reset|reset-batch`
- `GET/POST /api/rules`、`PUT/DELETE /api/rules/{id}`、`GET/PUT /api/settings`

## 目录
```
app.py config.py        # 入口 + 环境配置
db/ core/ routes/       # 持久化 / 业务（含规则引擎、防刷）/ HTTP 接入
frontend/               # Vue 3 + Vite + Tailwind 管理后台
```

MIT License，见 [LICENSE](LICENSE)。
