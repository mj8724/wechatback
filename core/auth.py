"""管理后台鉴权：Bearer token（主）+ 旧 ?pwd/body 密码（兼容）."""

import secrets
import time

from fastapi import HTTPException, Request

from core.security import (
    check_rate_limit,
    get_client_ip,
    is_valid_pwd,
    record_login_failure,
    record_login_success,
)
from db.database import get_db

TOKEN_TTL = 7 * 24 * 3600  # token 有效期 7 天


def issue_token() -> tuple:
    token = secrets.token_urlsafe(32)
    expires_at = time.time() + TOKEN_TTL
    conn = get_db()
    conn.execute(
        "INSERT INTO admin_tokens (token, expires_at) VALUES (?, ?)",
        (token, expires_at),
    )
    conn.commit()
    conn.close()
    return token, expires_at


def verify_token(token: str) -> bool:
    if not token:
        return False
    conn = get_db()
    row = conn.execute(
        "SELECT expires_at FROM admin_tokens WHERE token = ?", (token,)
    ).fetchone()
    if row is None:
        conn.close()
        return False
    if row["expires_at"] <= time.time():
        conn.execute("DELETE FROM admin_tokens WHERE token = ?", (token,))
        conn.commit()
        conn.close()
        return False
    conn.close()
    return True


def revoke_token(token: str):
    conn = get_db()
    conn.execute("DELETE FROM admin_tokens WHERE token = ?", (token,))
    conn.commit()
    conn.close()


def bearer_token(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:].strip()
    return ""


def require_admin(request: Request, pwd: str = ""):
    """管理接口鉴权：Bearer token 优先，旧 pwd 参数兼容。"""
    ip = get_client_ip(request)
    check_rate_limit(ip)

    if verify_token(bearer_token(request)):
        record_login_success(ip)
        return

    if pwd and is_valid_pwd(pwd):
        record_login_success(ip)
        return

    record_login_failure(ip)
    raise HTTPException(status_code=401, detail="密码错误")
