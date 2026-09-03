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


class ResetRequest(BaseModel):
    pwd: str = ""
    code: str = ""


class DeleteRequest(BaseModel):
    pwd: str = ""
    code: str = ""


class UserResetRequest(BaseModel):
    pwd: str = ""
    openid: str = ""


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
    duplicates = []
    seen = set()
    conn = get_db()
    cursor = conn.cursor()
    for code in req.codes:
        c = code.strip()
        if not c or c in seen:
            if c:
                duplicates.append(c)
            continue
        seen.add(c)
        cursor.execute("SELECT id FROM codes WHERE code = ?", (c,))
        if cursor.fetchone():
            duplicates.append(c)
            continue
        try:
            cursor.execute("INSERT INTO codes (code, status) VALUES (?, 'unused')", (c,))
            added += 1
        except Exception:
            duplicates.append(c)
    conn.commit()
    conn.close()
    return {"status": "success", "added": added, "duplicates": duplicates, "total": added + len(duplicates)}


@router.post("/api/codes/reset")
def reset_code(req: ResetRequest, request: Request):
    require_admin(request, req.pwd)
    code = (req.code or "").strip()
    if not code:
        raise HTTPException(status_code=400, detail="激活码不能为空")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM codes WHERE code = ?", (code,))
    row = cursor.fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="激活码不存在")
    if row["status"] != "assigned":
        conn.close()
        return {"status": "success", "reset": False, "message": "该激活码未被领取，无需重置"}

    cursor.execute(
        "UPDATE codes SET status = 'unused', assigned_openid = NULL, assigned_at = NULL WHERE code = ?",
        (code,)
    )
    cursor.execute("DELETE FROM users WHERE code = ?", (code,))
    conn.commit()
    conn.close()
    return {"status": "success", "reset": True, "message": "已重置为待领取，原领取人可重新领取"}


@router.post("/api/codes/delete")
def delete_code(req: DeleteRequest, request: Request):
    require_admin(request, req.pwd)
    code = (req.code or "").strip()
    if not code:
        raise HTTPException(status_code=400, detail="激活码不能为空")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM codes WHERE code = ?", (code,))
    row = cursor.fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="激活码不存在")

    was_assigned = row["status"] == "assigned"
    cursor.execute("DELETE FROM codes WHERE code = ?", (code,))
    cursor.execute("DELETE FROM users WHERE code = ?", (code,))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "已删除" + ("（原领取人绑定已解除）" if was_assigned else "" )}


@router.get("/api/users")
def list_users(request: Request, pwd: str = ""):
    require_admin(request, pwd)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM users")
    total = cursor.fetchone()["total"]
    cursor.execute("SELECT openid, code, created_at FROM users ORDER BY id DESC LIMIT 500")
    users = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"status": "success", "total": total, "users": users}


@router.post("/api/users/reset")
def reset_user(req: UserResetRequest, request: Request):
    require_admin(request, req.pwd)
    openid = (req.openid or "").strip()
    if not openid:
        raise HTTPException(status_code=400, detail="OpenID 不能为空")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT code FROM users WHERE openid = ?", (openid,))
    row = cursor.fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="该用户尚未领取激活码")

    code = row["code"]
    cursor.execute(
        "UPDATE codes SET status = 'unused', assigned_openid = NULL, assigned_at = NULL WHERE code = ?",
        (code,)
    )
    cursor.execute("DELETE FROM users WHERE openid = ?", (openid,))
    conn.commit()
    conn.close()
    return {"status": "success", "reset": True, "code": code, "message": f"已收回 {openid} 的激活码，其可重新领取"}
