from typing import Any, Dict

import core.config_store as cs
from db.database import db


def get_dashboard_stats() -> Dict[str, Any]:
    with db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM codes ORDER BY id DESC LIMIT 500")
        records = [dict(r) for r in cursor.fetchall()]

        cursor.execute("SELECT COUNT(*) as total FROM codes")
        total = cursor.fetchone()["total"]
        cursor.execute("SELECT COUNT(*) as used FROM codes WHERE status = 'assigned'")
        used = cursor.fetchone()["used"]
        cursor.execute("SELECT COUNT(*) as unused FROM codes WHERE status = 'unused'")
        unused = cursor.fetchone()["unused"]
        cursor.execute("SELECT COUNT(*) as users_count FROM users")
        users_count = cursor.fetchone()["users_count"]
        cursor.execute("SELECT COUNT(*) as unsubscribed_count FROM users WHERE last_event = 'unsubscribe'")
        unsubscribed_count = cursor.fetchone()["unsubscribed_count"]
        cursor.execute("SELECT COUNT(*) as messages_count FROM messages")
        messages_count = cursor.fetchone()["messages_count"]

        cursor.execute("""
            SELECT p.id, p.name, p.key, p.description, p.is_default,
                   COUNT(c.id) as total,
                   SUM(CASE WHEN c.status = 'assigned' THEN 1 ELSE 0 END) as used,
                   SUM(CASE WHEN c.status = 'unused' THEN 1 ELSE 0 END) as unused
            FROM code_pools p
            LEFT JOIN codes c ON p.id = c.pool_id
            GROUP BY p.id
            ORDER BY p.id ASC
        """)
        pools_stats = [dict(r) for r in cursor.fetchall()]
        for ps in pools_stats:
            ps["total"] = ps["total"] or 0
            ps["used"] = ps["used"] or 0
            ps["unused"] = ps["unused"] or 0

        cursor.execute("SELECT * FROM messages ORDER BY id DESC LIMIT 100")
        messages = [dict(r) for r in cursor.fetchall()]

        return {
            "total": total,
            "used": used,
            "unused": unused,
            "users_count": users_count,
            "unsubscribed_count": unsubscribed_count,
            "messages_count": messages_count,
            "pools": pools_stats,
            "messages": messages,
            "records": records,
            "token_configured": cs.is_wechat_configured(),
            "wechat_configured": cs.is_wechat_configured(),
            "setup_done": cs.is_setup_done(),
            "wechat_token_from_env": cs.is_wechat_token_from_env(),
            "website_url_from_env": cs.is_website_url_from_env(),
            "website": cs.get_website_url(),
            "group_id": cs.get_group_id(),
        }
