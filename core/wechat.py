import sqlite3
import time
from typing import Optional

import config
from core.rules import get_setting, load_rules, render
from db.database import db

MAX_ASSIGN_RETRIES = 5


def save_message(openid: str, msg_type: str, content: str):
    try:
        with db() as conn:
            conn.execute("INSERT INTO messages (openid, msg_type, content) VALUES (?, ?, ?)", (openid, msg_type, content))
            conn.commit()
    except Exception:
        pass


def _claim_code(conn, openid: str):
    """单次发码尝试。返回 (code, kind)，kind ∈ existing/new/empty/retry/error。"""
    cursor = conn.cursor()
    cursor.execute("SELECT code FROM users WHERE openid = ?", (openid,))
    row = cursor.fetchone()
    if row:
        return row["code"], "existing"

    cursor.execute("SELECT id, code FROM codes WHERE status = 'unused' ORDER BY id ASC LIMIT 1")
    code_row = cursor.fetchone()
    if not code_row:
        return None, "empty"

    code_id = code_row["id"]
    code_val = code_row["code"]
    now_str = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())

    try:
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute(
            "UPDATE codes SET status = 'assigned', assigned_openid = ?, assigned_at = ? WHERE id = ? AND status = 'unused'",
            (openid, now_str, code_id)
        )
        if cursor.rowcount == 0:
            conn.rollback()
            return None, "retry"

        cursor.execute("INSERT INTO users (openid, code) VALUES (?, ?)", (openid, code_val))
        conn.commit()
        return code_val, "new"
    except sqlite3.IntegrityError:
        # 并发下同 openid 已由另一请求写入：回滚后重读返回已领码
        conn.rollback()
        cursor.execute("SELECT code FROM users WHERE openid = ?", (openid,))
        row = cursor.fetchone()
        if row:
            return row["code"], "existing"
        return None, "retry"
    except Exception:
        conn.rollback()
        return None, "error"


def get_or_assign_code(openid: str) -> str:
    """兼容入口：按默认新码模板发码（规则引擎内部使用 render_code_reply）。"""
    if not openid:
        return "无法获取您的用户信息，请稍后重试。"
    code_val, kind = assign_code(openid)
    if kind == "retry" or kind == "error":
        return "系统繁忙，请稍后再试！"
    if kind == "empty":
        return get_setting("empty_reply")
    if kind == "existing":
        return render(get_setting("repeat_reply"), code_val)
    return render(get_setting("new_reply"), code_val)


def decide_reply(msg_type: str, event: str, content: str, from_user: str) -> Optional[str]:
    if msg_type == "event" and event in ["subscribe", "scan"]:
        return get_setting("welcome_reply")
    if msg_type != "text":
        return None
    t = content.strip().lower()
    for rule in load_rules():
        kw = (rule["keyword"] or "").lower()
        if not kw:
            continue
        hit = (t == kw) if rule["mode"] == "exact" else (kw in t)
        if not hit:
            continue
        if rule["action"] == "code":
            return render_code_reply(rule["content"], from_user)
        return render(rule["content"])
    return get_setting("fallback_reply")


def render_code_reply(template: str, openid: str) -> str:
    code_val, kind = assign_code(openid)
    if kind == "empty":
        return get_setting("empty_reply")
    if kind == "existing":
        return render(get_setting("repeat_reply"), code_val)
    if kind == "error":
        return "系统繁忙，请稍后再试！"
    return render(template, code_val)


def assign_code(openid: str):
    """发码并返回 (code, kind)，kind ∈ new/existing/empty/error。"""
    if not openid:
        return None, "error"
    code_val, kind = None, "retry"
    for _ in range(MAX_ASSIGN_RETRIES):
        with db() as conn:
            code_val, kind = _claim_code(conn, openid)
        if kind != "retry":
            break
    return code_val, kind


def build_reply_xml(from_user: str, to_user: str, reply_content: str) -> str:
    return f"""<xml>
<ToUserName><![CDATA[{from_user}]]></ToUserName>
<FromUserName><![CDATA[{to_user}]]></FromUserName>
<CreateTime>{int(time.time())}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[{reply_content}]]></Content>
</xml>"""
