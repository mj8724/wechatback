# WeChat Redeem Hub (wechatback)

<p align="center">
  <strong>开箱即用的微信公众号被动回复 & 多卡池激活码/卡密分发系统</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Vue-3.5+-4FC08D?style=flat&logo=vuedotjs&logoColor=white" alt="Vue 3">
  <img src="https://img.shields.io/badge/Vite-6.0+-646CFF?style=flat&logo=vite&logoColor=white" alt="Vite">
  <img src="https://img.shields.io/badge/TailwindCSS-3.4+-38B2AC?style=flat&logo=tailwind-css&logoColor=white" alt="TailwindCSS">
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=flat&logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg?style=flat" alt="License">
</p>

---

## 📖 项目简介

**WeChat Redeem Hub** 是专为微信公众号粉丝运营设计的全功能自动化系统。支持通过公众号关键词自动发码（一人一码/防超发/防重复领取），并集成了现代化 Vue 3 管理后台，涵盖多卡池管理、发码配方引擎、粉丝生命周期跟踪、对话成对审计流水、富文本占位符及生产高可用容灾。

不管是知识付费发放兑换码、社群裂变送体验券，还是自动化客户引导，本项目均可实现**分钟级部署、即插即用**。

---

## ✨ 核心特性

- 🚀 **极简上手（零配置启动）**：支持无需提前创建 `.env` 文件直接拉起；首次访问自动引导进入「网页初始化向导」设置管理密码与微信 Token，所有配置热更新即时生效。
- 🎟️ **多卡池与品类管理**：支持创建任意多个独立卡池（例如：默认池、会员月卡、AI 算力体验包），各卡池库存与发放独立统计。
- 🧪 **组合发码配方系统（Recipe Engine）**：支持在单条规则中配置跨卡池组合发码（例如：用户发送“新手礼包”，自动组合发放 1 个基础码 + 2 个体验码）；具备 **All-or-Nothing 事务原子性**，任一卡池缺货即安全回滚，杜绝部分发码造成的库存紊乱。
- 🤖 **灵活的关键词规则引擎**：支持模糊包含（contains）与精准等于（exact）匹配模式，内置规则优先级（priority）排序与一键启用开关；支持规则批量导入（JSON/Excel）、批量导出、批量启用/删除。
- 📝 **富文本模板与动态占位符**：发码文案支持 `{code}`（主码）、`{codes_map.xxx}`（指定卡池码）、`{site}`（兑换网站）、`{group}`（微信群入口）、`{openid}`、`{stock}`（当前库存）、`{date}`、`{time}` 等动态渲染。
- 👥 **粉丝全生命周期留存跟踪**：自动感知微信 `subscribe`（关注）与 `unsubscribe`（取消关注）事件，后台可直观筛选“领码后取关”用户，掌握粉丝留存率。
- 💬 **对话流水闭环审计**：粉丝发送的每一条原消息与系统自动回复成对落库归档，后台支持按关键词/OpenID 快速检索，支持一键导出 CSV。
- 🛡️ **生产级安全防护**：
  - 微信服务器签名 SHA1 严格校验 + 15 分钟时间戳防重放攻击；
  - 管理员密码采用行业标准 PBKDF2 安全哈希加盐存储；
  - 后台登录频控防爆破（IP 错误上限锁定 15 分钟）+ 7 天有效期 Bearer Token；
  - 微信入口支持基于客户端真实 IP 与 OpenID 的双层防刷节流；
  - 环境变量与数据库双模共存，环境变量声明项具有最高只读锁定权，防止后台误篡改。
- 🔄 **生产双轨部署与故障逃生（Host Fallback）**：针对边缘工控小主机（如 N5105/Debian13）可能出现的 Docker 底层用户态/内核兼容性崩溃，内置 Systemd 守护配置与 `./run-host.sh` 宿主机秒级逃生通道。

---

## 🛠️ 技术栈

| 领域 | 核心技术 | 说明 |
|---|---|---|
| **后端** | Python 3.11+ / FastAPI / Uvicorn | 异步高性能 Web 框架，提供 Restful API 与微信 XML 通信 |
| **数据库** | SQLite 3 (WAL 模式) | 零外部依赖、单文件存储、支持 IMMEDIATE 事务悲观并发锁 |
| **前端** | Vue 3 / Vite / Tailwind CSS / XLSX | 单页面现代管理后台，内置在单容器内静态服务，无需额外静态服务器 |
| **容器** | Docker (Multi-stage Build) | 锁死 Debian Bookworm 基础镜像，安全稳定，体积小巧 |
| **自动化测试** | Python Unittest (E2E Suite) | 涵盖卡池、配方发码、原子回滚、防刷鉴权等 10 项端到端全链路测试 |

---

## 🚀 快速开始

本项目支持两种运行方式，任选其一即可：

### 方式 A：零配置启动 + 网页向导（最省心，推荐）

无需提前手写任何配置文件，直接克隆启动：

```bash
# 1. 安装后端依赖
pip install -r requirements.txt

# 2. 构建前端静态资源
cd frontend && npm install && npm run build && cd ..

# 3. 启动服务（本地自动回退并初始化 ./data/wechat_redeem.db）
uvicorn app:app --host 0.0.0.0 --port 8000
```

启动后打开浏览器访问：`http://127.0.0.1:8000`
1. 系统自动进入**「首次初始化向导」**，设定管理员登录密码；
2. 在向导中可直接填入微信 Token、兑换网址与群微信号（亦可留空后续在总览随时配置）；
3. 保存后系统即刻就绪，**配置热更新即时生效，无需重启服务**。

---

### 方式 B：传统环境变量启动（适合 CI/CD 与自动化运维）

```bash
# 1. 从模板复制配置文件
cp .env.example .env

# 2. 编辑 .env 文件填入真实配置
# WECHAT_TOKEN=你的微信Token
# ADMIN_PASSWORD=你的管理员密码

# 3. 启动服务
pip install -r requirements.txt
cd frontend && npm install && npm run build && cd ..
set -a; source .env; set +a
uvicorn app:app --host 0.0.0.0 --port 8000
```

> **💡 说明**：通过 `.env` 注入的环境变量具有最高优先级，网页后台中对应字段将自动标记为「由环境变量托管」并变为只读，保证生产运维安全。

---

## 🐳 Docker 生产部署

推荐使用 Docker Compose 快速完成生产容器化部署：

```bash
# 1. 准备配置文件（若未填，可在启动后访问网页端配置）
cp .env.example .env

# 2. 构建并后台启动容器
docker compose up -d --build

# 3. 查看运行日志
docker compose logs -f
```

- 容器对外暴露 `8000` 端口。
- 数据库文件通过卷挂载持久化保存在宿主机的 `/opt/wechat-redeem/data`（可在 `docker-compose.yml` 中自定义调整）。

---

## 🌐 微信公众平台接入指引

1. 登录 [微信公众平台](https://mp.weixin.qq.com/)，进入 **设置与开发 -> 基本配置 -> 服务器配置**；
2. 点击「修改配置」：
   - **URL（服务器地址）**：`https://你的域名/wechat`（必须为公网可访问的 HTTPS 接口）
   - **Token（令牌）**：填写在系统后台或 `.env` 中设置的 `WECHAT_TOKEN`
   - **EncodingAESKey**：可随机生成（当前接口采用明文模式）
   - **消息加解密方式**：选择 **明文模式**
3. 先点击「提交」通过微信校验，再点击「启用」服务器配置；
4. 关注公众号并发送设置的关键词，即可收到自动回复与分配的激活码！

---

## 🧩 高级功能与配方语法

### 1. 模板占位符对照表

在 **后台 -> 回复设置** 或 **规则管理** 的回复文案中，可自由嵌入以下动态变量：

| 占位符 | 替换含义 | 示例值 |
|---|---|---|
| `{code}` | 当前分配的主激活码（单码或组合配方的首码） | `ABCD-1234-EFGH` |
| `{codes_map.<key>}` | 获取配方中指定卡池 key 领取的码（英文半角逗号分隔） | 见下文配方系统 |
| `{openid}` | 当前微信用户的 OpenID | `oK9...abc123` |
| `{site}` | 兑换/使用网站地址 | `https://your-site.com` |
| `{group}` | 微信社群入口微信号 | `wx_service_01` |
| `{stock}` | 默认卡池当前的未使用剩余库存 | `185` |
| `{date}` | 发放时的 UTC 日期 | `2026-09-26` |
| `{time}` | 发放时的 UTC 时间 | `10:30:00` |

### 2. 组合发码配方（Recipe）示例

在卡池管理中分别创建 key 为 `vip` 和 `gpt` 的卡池，导入相应码库。在规则的「发码配方」中填写：
```text
vip:1,gpt:2
```
回复内容模板可配置为：
```text
🎉 恭喜获得组合新手礼包！
尊贵月卡码：{codes_map.vip}
AI 体验额度码（2个）：
{codes_map.gpt}

请前往兑换网站：{site}
有疑问请联系微信：{group}
```
**原子性保证**：若 `vip` 卡池或 `gpt` 卡池中任一池库存不足，系统不会扣除任何码，直接安全返回告罄提示。

---

## ⚙️ 环境变量配置表

| 变量名 | 必填 | 默认值 | 说明 |
|---|---|---|---|
| `WECHAT_TOKEN` | 否 | 空 | 微信公众平台开发者 Token（留空可在网页后台总览直接配置） |
| `ADMIN_PASSWORD` | 否 | 空 | 后台管理密码，支持逗号分隔配置多个（留空时进入网页初始化向导） |
| `DB_PATH` | 否 | `/data/wechat_redeem.db` | SQLite 数据库存储路径（本地开发默认回退到 `./data/`） |
| `WEBSITE_URL` | 否 | `https://example.com` | 回复文案中 `{site}` 占位符内容，可在后台随时修改 |
| `GROUP_WECHAT_ID` | 否 | 空 | 回复文案中 `{group}` 占位符内容，可在后台随时修改 |
| `TRUST_PROXY_HEADERS` | 否 | `0` | 若经过 Cloudflare Tunnel 或 Nginx 反代，置为 `1` 以采信真实 IP |
| `ALLOWED_HOSTS` | 否 | 空 | HTTP Host 白名单校验（逗号分隔），生产可配置公网域名防 Host 投毒 |

---

## 🛡️ 生产容灾与宿主机逃生（Host Fallback）

针对工控小主机（如 N5105）、特定 Linux 新内核或容器底软出现未知兼容性故障（如 glibc 段错误 `Exit 139`）的场景，项目提供了经过线上真实故障验证的**宿主机快速逃生方案**：

```bash
# 1. 紧急止血：停止容器
docker update --restart=no wechat-redeem && docker stop wechat-redeem

# 2. 部署宿主机环境（若未配置）
python3 -m venv .venv-host
.venv-host/bin/pip install -r requirements.txt

# 3. 注册并启动 Systemd 守护
cp deploy/systemd/wechat-redeem-host.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now wechat-redeem-host
```
亦可直接使用内置运维脚本 `./run-host.sh` 一键切换。详见复盘总结：[`docs/INCIDENT_20260907_HOST_FALLBACK.md`](docs/INCIDENT_20260907_HOST_FALLBACK.md)。

---

## 🧪 自动化测试

项目内置端到端全链路自动化测试，覆盖所有核心业务边界：

```bash
python3 tests/test_features_e2e.py
```

测试覆盖用例：
- `[E2E-01]` 卡池 CRUD 与 key 命名规范校验
- `[E2E-02]` 多卡池批量导入、去重与独立库存统计
- `[E2E-03]` 规则引擎与组合发码配方保存
- `[E2E-04]` 多卡池组合发码事务与粉丝领码聚合
- `[E2E-05]` 重复发码幂等性（同 OpenID 领同码不重复扣减库存）
- `[E2E-06]` 组合发码库存不足 All-or-Nothing 原子事务安全回滚
- `[E2E-07]` 富文本动态占位符（openid, date, time, stock, group）渲染
- `[E2E-08]` 激活码级联收回与重新分配
- `[E2E-09]` 关键词规则批量导入（skip/overwrite）、批量启用与删除
- `[E2E-10]` 微信 Token 数据库热更新与无缝签名验证

---

## 📂 项目结构

```text
wechatback/
├── app.py                     # 应用主入口，静态资源挂载与中间件配置
├── config.py                  # 系统常量、安全参数、环境变量解析与默认值
├── requirements.txt           # Python 核心依赖清单
├── Dockerfile                 # 生产容器多阶段构建配置
├── docker-compose.yml         # 生产 Docker 容器编排文件
├── run-host.sh                # 宿主机容灾逃生快速启动脚本
├── core/                      # 核心业务逻辑层
│   ├── auth.py                # 管理员 Bearer Token 签发与过期校验
│   ├── config_store.py        # 数据库与环境变量双模配置中心（热更新管理）
│   ├── rules.py               # 规则匹配引擎与富模板占位符渲染器
│   ├── security.py            # IP/OpenID 防刷限流、哈希与加解密安全模块
│   └── wechat.py              # 微信 XML 解析生成、组合发码事务原子逻辑
├── db/                        # 数据库层
│   └── database.py            # SQLite 连接池、表初始化与平滑版本迁移
├── routes/                    # API 路由控制器
│   ├── api.py                 # 管理后台全量接口（统计/卡池/码库/规则/配置）
│   └── wechat.py              # 微信公众平台消息验证与被动回复接口
├── deploy/                    # 部署资产
│   └── systemd/               # 宿主机 systemd 服务单元配置文件
├── docs/                      # 架构文档与线上故障演练复盘
├── tests/                     # 自动化测试用例集
└── frontend/                  # Vue 3 现代化管理后台
    ├── src/                   # 前端源码（组件、路由、API、Tailwind 视图）
    ├── package.json           # 前端依赖配置
    └── vite.config.js         # Vite 构建与分块打包优化配置
```

---

## 📄 开源许可证

本项目基于 [MIT License](LICENSE) 开源。欢迎 Star、Fork 或提交 Pull Request！
