from typing import List

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

import config
from core.auth import bearer_token, issue_token, require_admin, revoke_token
from core.security import check_rate_limit, get_client_ip, is_valid_pwd, record_login_failure, record_login_success
from db.database import get_db

router = APIRouter()


class LoginRequest(BaseModel):
    pwd: str


class ImportRequest(BaseModel):
    pwd: str = ""
    codes: List[str] = []


@router.post("/api/login")
def login(req: LoginRequest, request: Request):
    ip = get_client_ip(request)
    check_rate_limit(ip)
    if not is_valid_pwd(req.pwd):
        record_login_failure(ip)
        raise HTTPException(status_code=401, detail="密码错误")
    record_login_success(ip)
    token, expires_at = issue_token()
    return {"status": "success", "token": token, "expires_at": expires_at}


@router.post("/api/logout")
def logout(request: Request):
    revoke_token(bearer_token(request))
    return {"status": "success"}


@router.get("/api/me")
def me(request: Request):
    require_admin(request)
    return {"status": "success"}


@router.get("/api/stats")
def get_stats(request: Request, pwd: str = ""):
    require_admin(request, pwd)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM codes")
    total = cursor.fetchone()["total"]
    cursor.execute("SELECT COUNT(*) as used FROM codes WHERE status = 'assigned'")
    used = cursor.fetchone()["used"]
    cursor.execute("SELECT COUNT(*) as unused FROM codes WHERE status = 'unused'")
    unused = cursor.fetchone()["unused"]
    cursor.execute("SELECT COUNT(*) as users_count FROM users")
    users_count = cursor.fetchone()["users_count"]
    cursor.execute("SELECT COUNT(*) as messages_count FROM messages")
    messages_count = cursor.fetchone()["messages_count"]

    cursor.execute("SELECT * FROM messages ORDER BY id DESC LIMIT 100")
    messages = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT id, code, status, assigned_openid, assigned_at, created_at FROM codes ORDER BY id DESC LIMIT 500")
    records = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return {
        "total": total,
        "used": used,
        "unused": unused,
        "users_count": users_count,
        "messages_count": messages_count,
        "messages": messages,
        "records": records,
        "token": config.WECHAT_TOKEN,
        "website": config.WEBSITE_URL
    }


@router.post("/api/import")
def import_codes(req: ImportRequest, request: Request):
    require_admin(request, req.pwd)

    added = 0
    conn = get_db()
    cursor = conn.cursor()
    for code in req.codes:
        c = code.strip()
        if not c:
            continue
        try:
            cursor.execute("INSERT OR IGNORE INTO codes (code, status) VALUES (?, 'unused')", (c,))
            if cursor.rowcount > 0:
                added += 1
        except Exception:
            pass
    conn.commit()
    conn.close()
    return {"status": "success", "added": added}
