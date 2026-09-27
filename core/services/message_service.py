from typing import List, Tuple

from core.security import escape_like
from db.database import db


def save_message(openid: str, msg_type: str, content: str, reply_content: str = ""):
    """持久化消息与回复成对流水。"""
    try:
        with db() as conn:
            conn.execute(
                "INSERT INTO messages (openid, msg_type, content, reply_content) VALUES (?, ?, ?, ?)",
                (openid, msg_type, content, reply_content or ""),
            )
            conn.commit()
    except Exception:
        pass


def list_messages(
    q: str = "",
    limit: int = 100,
    offset: int = 0,
) -> Tuple[int, List[dict]]:
    limit = max(1, min(limit, 500))
    offset = max(0, offset)
    with db() as conn:
        cursor = conn.cursor()
        if q.strip():
            like = f"%{escape_like(q.strip())}%"
            cursor.execute(
                "SELECT COUNT(*) as total FROM messages WHERE openid LIKE ? ESCAPE '\\' OR content LIKE ? ESCAPE '\\' OR reply_content LIKE ? ESCAPE '\\'",
                (like, like, like),
            )
            total = cursor.fetchone()["total"]
            cursor.execute(
                "SELECT id, openid, msg_type, content, reply_content, created_at FROM messages "
                "WHERE openid LIKE ? ESCAPE '\\' OR content LIKE ? ESCAPE '\\' OR reply_content LIKE ? ESCAPE '\\' "
                "ORDER BY id DESC LIMIT ? OFFSET ?", (like, like, like, limit, offset))
        else:
            cursor.execute("SELECT COUNT(*) as total FROM messages")
            total = cursor.fetchone()["total"]
            cursor.execute(
                "SELECT id, openid, msg_type, content, reply_content, created_at FROM messages "
                "ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset))
        messages = [dict(r) for r in cursor.fetchall()]
        return total, messages
