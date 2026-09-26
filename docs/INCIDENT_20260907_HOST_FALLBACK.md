# 2026-09-07 线上故障复盘：容器底软崩溃与宿主机逃生实战

## 故障现象
- **时间**：2026-09-07 16:58
- **现象**：线上 `wechat-redeem` Docker 容器首次因 `Exit 139 (SIGSEGV)` 崩溃并陷入无限重启循环。
- **影响**：Cloudflare Tunnel 报错 `dial tcp [::1]:8000 connection refused`，公网 `wx.liubaitech.cn` 返回 502 / 无法访问。

## 根因定位边界
1. **容器内故障现象**：容器内部 Python 3.11 解释器凡执行 `python -c "..."` 均必定抛出 `SIGSEGV (139)`，但 `python --version` / `python --help` 存活。
2. **官方原版复现**：官方 `python:3.11-slim-bookworm` 干净镜像同样稳定复现该问题；而普通的 hello-world 或 C 编译程序在容器内正常，排除了业务代码本身与单个镜像层损坏的原因。
3. **宿主环境对比**：宿主机系统为 Debian 13（内核 6.12.101，Intel N5105 工控小主机），宿主机自带的 Python 3.13.5 运行一切正常。
4. **内核与底层定位**：`dmesg` 捕获到 `segfault in libpython3.11.so.1.0 (error 7)`。推断为容器 Python 3.11 用户态与宿主机新内核/overlayfs（containerd snapshotter）在特定硬件架构下的深层兼容性异常。

## 紧急止血方案
1. **防止抢占端口与无限重启**：
   ```bash
   docker update --restart=no wechat-redeem
   docker stop wechat-redeem
   ```
2. **启动宿主机原生虚拟环境（Host Fallback）**：
   * 创建隔离环境：`/opt/wechat-redeem/.venv-host`（基于宿主机稳定的 Python 3.13）
   * 恢复前端静态资源：从容器镜像提取 `frontend/dist` 到宿主目录。
   * 配置托管守护：创建 `systemd` 服务 `wechat-redeem-host.service`，通过 `run-host.sh` 加载配置与指定数据库路径，监听 `127.0.0.1:8000` 直连 Cloudflare Tunnel。

## 业务验证（18:09 全部恢复）
* 本地健康检测：`GET /` (200), `GET /admin` (200), `GET /wechat` (403 签名防御正常), `GET /api/stats` (401 未登录正常)
* 公网链路恢复：https://wx.liubaitech.cn/ 访问正常，延迟 ~1.4s，数据库 80K 数据完好无损。
* 服务随宿主机重启由 systemd 自动拉起。

## 生产经验与启示
1. **多环境部署冗余**：容器化并不是万能银弹，在边缘工控设备或轻量云主机上，必须准备 `run-host.sh` 与 systemd 配置作为“一键逃生通道”。
2. **快速止血优先级高于深入调试**：线上不可用时，先切宿主 venv 止血，后续再排查底层 glibc/内核段错误。
