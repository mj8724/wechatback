"""关键词回复规则引擎：规则按 priority 首个命中；占位符 {code} {site} {group}。"""

import config
from db.database import db


def load_rules():
    with db() as conn:
        rows = conn.execute(
            "SELECT id, keyword, mode, action, content, priority, enabled "
            "FROM keyword_rules WHERE enabled = 1 ORDER BY priority ASC, id ASC"
        ).fetchall()
        return [dict(r) for r in rows]


def list_all_rules():
    with db() as conn:
        rows = conn.execute(
            "SELECT id, keyword, mode, action, content, priority, enabled, created_at "
            "FROM keyword_rules ORDER BY priority ASC, id ASC"
        ).fetchall()
        return [dict(r) for r in rows]


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


def render(template: str, code: str = "") -> str:
    return (
        (template or "")
        .replace("{code}", code or "")
        .replace("{site}", config.WEBSITE_URL)
        .replace("{group}", get_setting("group_id", config.GROUP_WECHAT_ID))
    )
