import os


def _required(name: str) -> str:
    val = os.environ.get(name, "").strip()
    if not val:
        raise RuntimeError(f"缺少必需环境变量 {name}，请复制 .env.example 为 .env 并填写后启动")
    return val


DB_PATH = os.environ.get("DB_PATH", "/data/wechat_redeem.db")
WECHAT_TOKEN = _required("WECHAT_TOKEN")
# 管理密码仅来自环境变量（逗号分隔可配多个），代码与仓库中不得出现明文密码
ADMIN_PASSWORDS = {p.strip() for p in _required("ADMIN_PASSWORD").split(",") if p.strip()}
WEBSITE_URL = os.environ.get("WEBSITE_URL", "https://newapi.liubaitech.cn")
GROUP_WECHAT_ID = "810466205"  # 微信群：添加此微信号

# ----------------- 防暴力破解配置 -----------------
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION = 15 * 60

# ----------------- 微信消息入口配置 -----------------
# POST body 上限（微信文本消息远小于此值）
WECHAT_MAX_BODY = 64 * 1024
# 签名时间戳容忍窗口（秒），防重放
WECHAT_TS_WINDOW = 600
# 每 IP 每分钟允许的 /wechat 请求数
WECHAT_RATE_PER_MIN = 30
