import os

DB_PATH = os.environ.get("DB_PATH", "/data/wechat_redeem.db")
WECHAT_TOKEN = os.environ.get("WECHAT_TOKEN", "REDACTED-WECHAT-TOKEN")
# 支持密码：REDACTED-PASSWORD 或 REDACTED-PASSWORD
ADMIN_PASSWORDS = {"REDACTED-PASSWORD", "REDACTED-PASSWORD", os.environ.get("ADMIN_PASSWORD", "REDACTED-PASSWORD")}
WEBSITE_URL = os.environ.get("WEBSITE_URL", "https://newapi.liubaitech.cn")
GROUP_WECHAT_ID = "810466205"  # 微信群：添加此微信号

# ----------------- 防暴力破解配置 -----------------
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION = 15 * 60
