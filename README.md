# WeChat Redeem Hub (wechatback)

<p align="center">
  <strong>开箱即用的微信公众号被动回复 & 多卡池激活码/卡密分发系统</strong>
</p>

<p align="center">
  <a href="https://github.com/mj8724/wechatback/actions/workflows/ci.yml">
    <img src="https://github.com/mj8724/wechatback/actions/workflows/ci.yml/badge.svg" alt="CI">
  </a>
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.109+-009688?style=flat&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Vue-3.5+-4FC08D?style=flat&logo=vuedotjs&logoColor=white" alt="Vue 3">
  <img src="https://img.shields.io/badge/Vite-6.0+-646CFF?style=flat&logo=vite&logoColor=white" alt="Vite">
  <img src="https://img.shields.io/badge/TailwindCSS-3.4+-38B2AC?style=flat&logo=tailwind-css&logoColor=white" alt="TailwindCSS">
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=flat&logo=docker&logoColor=white" alt="Docker">
  <a href="https://polyformproject.org/licenses/noncommercial/1.0.0/"><img src="https://img.shields.io/badge/License-PolyForm--Noncommercial--1.0.0-blue.svg?style=flat" alt="License: PolyForm Noncommercial 1.0.0"></a>
</p>

---

## 📖 项目简介

**WeChat Redeem Hub** 是专为微信公众号自动化运营打造的高性能服务系统。支持通过公众号发送关键词自动分发卡密/激活码（一人一码、防超发、防重复领取），并集成了现代化 Vue 3 极简管理后台，涵盖**多卡池管理、发码配方引擎、全局动态变量中心、全规则统一调度、粉丝生命周期留存分析、成对流水审计、HelpTip 视觉降噪交互及生产双轨容灾**。

不管是知识付费发放兑换码、社群裂变送体验券，还是自动化客户引导，本项目均可实现**分钟级部署、即插即用**。

---

## ✨ 核心特性

- 🚀 **极简上手（零配置启动向导）**：无需提前创建 `.env` 文件即可直接拉起；首次访问自动引导进入「网页初始化向导」设置管理密码与微信 Token，所有配置热更新即时生效。
- 🎟️ **多卡池与品类管理**：支持创建任意多个独立卡池（例如：默认池、会员月卡、AI 算力体验包），各卡池库存、发放与激活独立统计。
- 🧪 **组合发码配方系统（Recipe Engine）**：支持单条规则跨品类组合发码（例如：用户发送“新手礼包”，自动组合发放 1 个基础码 + 2 个体验码）；具备 **All-or-Nothing 事务悲观锁原子性**，任一卡池缺货即安全回滚，杜绝部分发码造成的库存紊乱。
- 🌐 **全局自定义变量中心（随处动态调用）**：
  - 内置 `site`（兑换网址）与 `group`（客服微信号）；
  - 支持管理员任意添加 `notice`、`help_url` 等自定义变量；
  - 在所有回复文案中输入 `{变量名}` 即可自动注入对应内容，修改变量全局即时生效。
- 🤖 **全规则统一调度引擎（包含 / 全等 / 正则 / 事件）**：
  - 关键词支持包含模糊匹配、全等精准匹配及**高级正则表达式（Regex）**模式；
  - 关注欢迎语（`event_subscribe`）与默认兜底回复（`event_fallback`）全面收归统一规则列表，**所有规则均支持一键独立开关**。
- 💬 **发码三态分支独立文案（拒绝写死）**：
  - 针对发码规则，原生支持独立的 **首次成功**、**重复领取提醒**、**库存告罄缺货** 三大状态分支回复文案；
  - 可选开启 **活动有效时间限制**（包含活动未开始与已结束自动拦截提示）。
- 🎨 **专业紧凑 UI 与 HelpTip 悬浮气泡**：
  - 全面视觉降噪，去除说教型长句与括号文字；
  - 所有操作指导与格式说明均收拢至关键名词旁的问号小图标中，**鼠标悬浮即时弹出优雅深色气泡说明**；
  - 规则列表与全局变量采用轻量级二级选项卡隔离，告别页面上下无限堆叠。
- 👥 **粉丝生命周期跟踪与闭环流水审计**：
  - 自动感知微信 `subscribe`（关注）与 `unsubscribe`（取消关注）事件，后台直观筛选“领码后取关”用户，掌握留存率；
  - 粉丝发送原消息与系统自动回复成对落库归档，支持全文检索与一键导出 Excel / CSV。
- 🏛️ **分层解耦架构设计**：
  - 遵循 `Routes -> Services -> Infrastructure` 单向依赖，数据库操作 100% 收敛至领域服务层，路由层 0 原生 SQL；
  - 微信通信协议与业务决策彻底解耦，为未来接入飞书、企微或网页发码提供即插即用复用能力。
- 🔄 **生产双轨部署与故障逃生（Host Fallback）**：针对工控机或特定 Linux 内核下的 Docker 底层兼容性异常（如 glibc 段错误 Exit 139），内置 Systemd 守护配置与 `./run-host.sh` 宿主机秒级逃生通道。

---

## 🛠️ 技术栈

| 领域 | 核心技术 | 说明 |
|---|---|---|
| **后端框架** | Python 3.11+ / FastAPI / Uvicorn | 异步高性能 Web 框架，提供 Restful API 与微信 XML 通信 |
| **数据库** | SQLite 3 (WAL 模式) | 零外部依赖、单文件存储、支持 IMMEDIATE 事务悲观并发锁 |
| **前端栈** | Vue 3 / Vite 6 / Tailwind CSS / XLSX | 单页面现代管理后台，内置在单容器内静态服务，无需额外反向代理 |
| **服务分层** | 独立 DTO 契约 + 领域服务层 (Services) | code_service, user_service, dispatch_service, message_service 等 |
| **持续集成** | GitHub Actions (CI) | 涵盖 Python 3.11/3.12、Node 20 前端打包与 Docker 多阶段构建 |

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

# 3. 启动服务（自动加载 .env，本地自动回退到 ./data/wechat_redeem.db）
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
uvicorn app:app --host 0.0.0.0 --port 8000
```

> **💡 说明**：通过 `.env` 注入的环境变量具有最高优先级，网页后台中对应字段将自动标记为「由环境变量托管」并变为只读，保证生产运维安全。

---

## 🔐 管理员登录与密码

- **默认/环境变量密码**：启动时会自动读取根目录 `.env` 中的 `ADMIN_PASSWORD` 字段。
- **首次向导设置密码**：若启动时未配置环境变量，访问 `http://127.0.0.1:8000/setup` 时设置的管理员密码会被安全加盐（PBKDF2-SHA256）存储于数据库中。
- **修改密码**：登录后台后，随时可以在 **总览 -> 系统配置** 中直接输入新密码热更新。

---

## 🌐 微信公众平台接入指引

1. 登录 [微信公众平台](https://mp.weixin.qq.com/)，进入 **设置与开发 -> 基本配置 -> 服务器配置**；
2. 点击「修改配置」：
   - **URL（服务器地址）**：`https://你的公网域名/wechat`（必须为公网可访问的 HTTPS 接口）
   - **Token（令牌）**：填写在系统后台或 `.env` 中设置的 `WECHAT_TOKEN`
   - **EncodingAESKey**：可随机生成（当前接口采用明文模式）
   - **消息加解密方式**：选择 **明文模式**
3. 先点击「提交」通过微信校验，再点击「启用」服务器配置；
4. 关注公众号并发送设置的关键词，即可收到自动回复与分配的激活码！

---

## 🧩 动态占位符与配方速查

### 1. 回复文案动态占位符

在规则文案中，可自由嵌入以下动态标签（或直接点击编辑区上的微标签胶囊插入）：

| 占位符 | 替换含义 | 示例值 |
|---|---|---|
| `{code}` | 当前分配的主卡密（单码或组合配方的首码） | `ABCD-1234-EFGH` |
| `{codes}` | 结构化多品类卡密清单（带品类名称） | `【默认池】：CODE-01\n【AI算力】：GPT-01` |
| `{code.<key>}` | 获取配方中指定卡池 key 领取的码（逗号分隔） | `GPT-01, GPT-02` |
| `{openid}` | 当前微信用户的 OpenID | `oK9...abc123` |
| `{site}` | 兑换/使用网站地址（取自全局变量） | `https://your-site.com` |
| `{group}` | 微信社群入口微信号（取自全局变量） | `wx_service_01` |
| `{stock}` | 全品类卡池当前的未领剩余库存概览 | `默认卡券池: 88, AI算力: 12` |
| `{date}` | 发放时的 UTC 日期 | `2026-09-27` |
| `{time}` | 发放时的 UTC 时间 | `15:30:00` |
| `{任意自定义key}` | 匹配「全局变量」中设置的任意 Key | 对应填写的变量值 |

### 2. Excel 批量导入格式规范

进入 **激活码管理 -> 批量导入 -> Excel 导入**：
- 第一行必须为【列头】（对应卡池 key 或卡池名称，如 `default`、`gpt`、`vip`）；
- 从第二行开始每行填写一个激活码，系统支持单列或多列并排导入并自动分类；
- 界面内提供 **“📥 下载标准模板 (.xlsx)”**，点击即可直接下载示例文件！

```text
| default (默认池)  | gpt (AI算力)     | vip (月卡会员)    |
|-------------------|------------------|-------------------|
| CODE-DEF-001      | CODE-GPT-001     | CODE-VIP-001      |
| CODE-DEF-002      | CODE-GPT-002     | CODE-VIP-002      |
```

---

## 🐳 Docker 生产部署

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

项目内置端到端全链路自动化测试，覆盖所有核心业务与边界：

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
- `[E2E-11]` 全局自定义变量 CRUD、防删保护与动态注入
- `[E2E-12]` 正则表达式关键词规则模式匹配与拦截
- `[E2E-13]` 发码 3 状态独立分支（首发成功/重复已领/缺货告罄）返回
- `[E2E-14]` 活动时间限制窗口拦截（未开始 / 已结束）
- `[E2E-15]` 系统事件规则（关注欢迎语 / 兜底回复）独立开关与静默控制

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
├── core/                      # 核心业务与领域层
│   ├── schemas/               # 独立 DTO 契约层 (请求/响应模型)
│   ├── services/              # 核心领域服务层
│   │   ├── code_service.py    # 卡池 CRUD、去重导入、配方悲观锁发码事务
│   │   ├── user_service.py    # 粉丝生命周期、Claims聚合、级联解绑重置
│   │   ├── dispatch_service.py# 渠道无关的业务决策调度与分支渲染引擎
│   │   ├── message_service.py # 消息与回复闭环流水持久化与分页检索
│   │   ├── config_service.py  # 初始化向导与参数更新协同
│   │   └── stats_service.py   # 仪表盘指标全量聚合汇总
│   ├── auth.py                # 管理员 Bearer Token 签发与过期校验
│   ├── config_store.py        # 底层凭据存储与只读环境变量判断
│   ├── rules.py               # 富模板占位符渲染与全局变量管理
│   ├── security.py            # IP/OpenID 防刷限流、哈希与加解密安全模块
│   └── wechat.py              # 微信通信协议适配器 (XML 解析与构建)
├── db/                        # 数据库层
│   └── database.py            # SQLite 连接池、表初始化与平滑版本迁移
├── routes/                    # 控制器层 (无 SQL 裸写)
│   ├── api.py                 # 管理后台全量 Restful API
│   └── wechat.py              # 微信公众平台消息验证与被动回复接口
├── deploy/                    # 部署资产 (systemd 守护单元)
├── docs/                      # 架构文档与线上故障演练复盘
├── tests/                     # 自动化测试用例集
└── frontend/                  # Vue 3 现代化管理后台
    ├── src/                   # 前端源码（组件、路由、API、Tailwind 视图）
    ├── package.json           # 前端依赖配置
    └── vite.config.js         # Vite 构建与分块打包优化配置
```

---

## 📄 许可证与商业使用

本项目采用 [PolyForm Noncommercial License 1.0.0](LICENSE)，**不再采用 MIT 协议**。该许可仅授权非商业用途；**禁止任何商业用途，包括出售、收费分发，或在商业运营中使用本项目，即使服务免费提供也不代表允许商用**。个人学习、实验及符合许可证定义的非商业用途除外；具体以许可证原文为准。

如需将本项目用于商业用途，请在使用前联系版权方并取得单独的书面商业授权。
