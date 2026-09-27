import hashlib
import hmac
import os
import secrets

# 自动加载同级 .env 配置文件（若存在且未在系统环境变量中定义）
_env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.isfile(_env_file):
    try:
        with open(_env_file, "r", encoding="utf-8") as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith("#") and "=" in _line:
                    _k, _v = _line.split("=", 1)
                    _k = _k.strip()
                    _v = _v.strip().strip("'\"")
                    if _k and _k not in os.environ:
                        os.environ[_k] = _v
    except Exception:
        pass

_env_db = os.environ.get("DB_PATH", "").strip()
if _env_db:
    DB_PATH = _env_db
else:
    # 宿主机非 root 环境下 /data 通常不可写，自动回退到项目本地 data 目录
    _base_dir = os.path.dirname(os.path.abspath(__file__))
    try:
        if os.path.exists("/data") and os.access("/data", os.W_OK):
            DB_PATH = "/data/wechat_redeem.db"
        else:
            DB_PATH = os.path.join(_base_dir, "data", "wechat_redeem.db")
    except Exception:
        DB_PATH = os.path.join(_base_dir, "data", "wechat_redeem.db")

# 占位符常量：若环境变量为这些默认占位符，视作未配置
PLACEHOLDER_TOKENS = {"your-wechat-token-here", "wechat-token-here", "change-me"}
PLACEHOLDER_PASSWORDS = {"change-me", "your-password-here", "admin"}
PLACEHOLDER_WEBSITE_URLS = {"https://example.com", "http://example.com"}

# 环境变量原始读取（允许缺失，缺失时不阻断启动）
_env_token = os.environ.get("WECHAT_TOKEN", "").strip()
ENV_WECHAT_TOKEN = "" if _env_token in PLACEHOLDER_TOKENS else _env_token
WECHAT_TOKEN = ENV_WECHAT_TOKEN  # 兼容现有静态引用

_env_pwd = os.environ.get("ADMIN_PASSWORD", "").strip()
ADMIN_PASSWORDS = {
    p.strip().replace("！", "!")
    for p in _env_pwd.split(",")
    if p.strip() and p.strip() not in PLACEHOLDER_PASSWORDS
}

_env_website = os.environ.get("WEBSITE_URL", "").strip()
DEFAULT_WEBSITE_URL = "https://newapi.liubaitech.cn"
ENV_WEBSITE_URL = "" if _env_website in PLACEHOLDER_WEBSITE_URLS else _env_website
WEBSITE_URL = ENV_WEBSITE_URL or DEFAULT_WEBSITE_URL

GROUP_WECHAT_ID = os.environ.get("GROUP_WECHAT_ID", "").strip()

# ----------------- 防暴力破解配置 -----------------
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION = 15 * 60

# ----------------- 微信消息入口配置 -----------------
# POST body 上限（微信文本消息远小于此值）
WECHAT_MAX_BODY = 64 * 1024
# 签名时间戳容忍窗口（秒），防重放
WECHAT_TS_WINDOW = 600
# 每 IP 每分钟允许的 /wechat 请求数（微信出口 IP 集中，阈值放宽）
WECHAT_RATE_PER_MIN = 150
# 每 OpenID 每分钟允许的 /wechat 请求数（细粒度防刷）
WECHAT_RATE_PER_OPENID = 10

# ----------------- 密码哈希纯函数 (PBKDF2-HMAC-SHA256) -----------------
PBKDF2_ITERATIONS = 200_000


def hash_password(password: str) -> str:
    """计算密码的 PBKDF2-HMAC-SHA256 哈希值（200,000次迭代）。"""
    salt = secrets.token_hex(16)
    canon = (password or "").strip().replace("！", "!")
    key = hashlib.pbkdf2_hmac("sha256", canon.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${key.hex()}"


def verify_password_hash(password: str, stored_hash: str) -> bool:
    """校验密码是否匹配存储的哈希字符串。"""
    if not password or not stored_hash:
        return False
    parts = stored_hash.split("$")
    if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
        return False
    try:
        iterations = int(parts[1])
        salt = parts[2]
        expected_hex = parts[3]
        canon = password.strip().replace("！", "!")
        key = hashlib.pbkdf2_hmac("sha256", canon.encode("utf-8"), salt.encode("utf-8"), iterations)
        return hmac.compare_digest(key.hex(), expected_hex)
    except Exception:
        return False

