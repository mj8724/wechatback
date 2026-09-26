"""系统配置持久化与运行时状态维护 (site_settings)"""

import config
from db.database import db


def get_setting(key: str, default: str = "") -> str:
    with db() as conn:
        row = conn.execute("SELECT value FROM site_settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default


def set_setting(key: str, value: str):
    with db() as conn:
        conn.execute(
            "INSERT INTO site_settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        conn.commit()


def get_wechat_token() -> str:
    """获取生效的微信 Token：环境变量优先，其次数据库配置。"""
    if config.ENV_WECHAT_TOKEN:
        return config.ENV_WECHAT_TOKEN
    return get_setting("wechat_token", "").strip()


def is_wechat_token_from_env() -> bool:
    return bool(config.ENV_WECHAT_TOKEN)


def is_wechat_configured() -> bool:
    return bool(get_wechat_token())


def get_website_url() -> str:
    """获取生效的兑换网站 URL：环境变量优先，其次数据库，默认兜底。"""
    if config.ENV_WEBSITE_URL:
        return config.ENV_WEBSITE_URL
    db_url = get_setting("website_url", "").strip()
    return db_url or config.DEFAULT_WEBSITE_URL


def is_website_url_from_env() -> bool:
    return bool(config.ENV_WEBSITE_URL)


def get_group_id() -> str:
    """获取生效的群微信号：环境变量优先，其次数据库。"""
    if config.GROUP_WECHAT_ID:
        return config.GROUP_WECHAT_ID
    return get_setting("group_id", "").strip()


def is_group_id_from_env() -> bool:
    return bool(config.GROUP_WECHAT_ID)


def has_db_admin_password() -> bool:
    return bool(get_setting("admin_pwd_hash", "").strip())


def is_setup_done() -> bool:
    """系统是否已经完成初始化：有环境变量管理密码或已设置数据库管理密码。"""
    return bool(config.ADMIN_PASSWORDS) or has_db_admin_password()


def set_admin_password(new_pwd: str):
    """设置数据库管理员密码哈希（长度要求 >= 8）。"""
    pwd = (new_pwd or "").strip()
    if len(pwd) < 8:
        raise ValueError("管理员密码长度至少为 8 位")
    hashed = config.hash_password(pwd)
    set_setting("admin_pwd_hash", hashed)


def verify_admin_password(pwd: str) -> bool:
    """校验管理员密码：优先匹配环境变量集合，其次匹配数据库哈希。"""
    if not pwd:
        return False
    canon = pwd.strip().replace("！", "!")
    if canon in config.ADMIN_PASSWORDS:
        return True
    stored_hash = get_setting("admin_pwd_hash", "").strip()
    if stored_hash and config.verify_password_hash(canon, stored_hash):
        return True
    return False


def mask_token(token: str) -> str:
    """掩码微信 Token，避免完全泄露但可用于确认。"""
    t = (token or "").strip()
    if not t:
        return ""
    if len(t) <= 6:
        return "***"
    return f"{t[:3]}***{t[-3:]}"
