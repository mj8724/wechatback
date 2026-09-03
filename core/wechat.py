import sqlite3
import time
from typing import Optional

import config
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
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")

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
    if not openid:
        return "无法获取您的用户信息，请稍后重试。"

    code_val, kind = None, "retry"
    for _ in range(MAX_ASSIGN_RETRIES):
        with db() as conn:
            code_val, kind = _claim_code(conn, openid)
        if kind != "retry":
            break

    if kind == "retry" or kind == "error":
        return "系统繁忙，请稍后再试！"
    if kind == "empty":
        return f"抱歉，当前激活码已被领完，请稍后再试或联系管理员！\n平台地址：{config.WEBSITE_URL}"
    if kind == "existing":
        return (
            f"您之前已成功领取过专属激活码：\n\n"
            f"【{code_val}】\n\n"
            f"👉 兑换地址：{config.WEBSITE_URL}\n"
            f"每个用户限领一次，已领取的激活码可随时在上方平台完成兑换！"
        )
    return (
        f"🎉 您的专属激活码为：\n\n"
        f"【{code_val}】\n\n"
        f"👉 兑换地址：{config.WEBSITE_URL}\n\n"
        f"每个用户限领一次，请前往上方兑换地址完成充值兑换！"
    )


def decide_reply(msg_type: str, event: str, content: str, from_user: str) -> Optional[str]:
    reply_content = None
    if msg_type == "event" and event in ["subscribe", "scan"]:
        reply_content = (
            f"🎉 欢迎关注！\n\n"
            f"发送【激活码】，即可获取您的专属激活码（每个用户限领一次）\n\n"
            f"发送【微信群】，即可获取微信群入口，一起交流！"
        )
    elif msg_type == "text":
        t = content.strip().lower()
        if "激活码" in t or "激活" in t or "兑换码" in t:
            reply_content = get_or_assign_code(from_user)
        elif "微信群" in t or "加群" in t or ("群" in t and "激活" not in t):
            reply_content = (
                f"📱 请添加我的微信号：{config.GROUP_WECHAT_ID}\n\n"
                f"添加时备注【进群】，我会拉您进入微信群，一起交流！"
            )
        else:
            reply_content = (
                f"👋 收到您的留言！\n\n"
                f"• 发送【激活码】→ 获取专属激活码\n"
                f"• 发送【微信群】→ 获取微信群入口\n"
                f"• 每个用户限领一次激活码"
            )
    return reply_content


def build_reply_xml(from_user: str, to_user: str, reply_content: str) -> str:
    return f"""<xml>
<ToUserName><![CDATA[{from_user}]]></ToUserName>
<FromUserName><![CDATA[{to_user}]]></FromUserName>
<CreateTime>{int(time.time())}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[{reply_content}]]></Content>
</xml>"""
