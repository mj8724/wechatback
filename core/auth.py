"""管理后台鉴权：只认 Authorization: Bearer token."""

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
from db.database import db

TOKEN_TTL = 7 * 24 * 3600  # token 有效期 7 天


def issue_token() -> tuple:
    token = secrets.token_urlsafe(32)
    expires_at = time.time() + TOKEN_TTL
    with db() as conn:
        conn.execute(
            "INSERT INTO admin_tokens (token, expires_at) VALUES (?, ?)",
            (token, expires_at),
        )
        conn.commit()
    return token, expires_at


def verify_token(token: str) -> bool:
    if not token:
        return False
    with db() as conn:
        row = conn.execute(
            "SELECT expires_at FROM admin_tokens WHERE token = ?", (token,)
        ).fetchone()
        if row is None:
            return False
        if row["expires_at"] <= time.time():
            conn.execute("DELETE FROM admin_tokens WHERE token = ?", (token,))
            conn.commit()
            return False
    return True


def revoke_token(token: str):
    if not token:
        return
    with db() as conn:
        conn.execute("DELETE FROM admin_tokens WHERE token = ?", (token,))
        conn.commit()


def bearer_token(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:].strip()
    return ""


def require_admin(request: Request):
    """管理接口鉴权：只认 Authorization: Bearer token。"""
    ip = get_client_ip(request)
    check_rate_limit(ip)

    if verify_token(bearer_token(request)):
        record_login_success(ip)
        return

    record_login_failure(ip)
    raise HTTPException(status_code=401, detail="未登录或登录已过期")
