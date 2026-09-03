from typing import List

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

import config
from core.auth import bearer_token, issue_token, require_admin, revoke_token
from core.security import check_rate_limit, get_client_ip, is_valid_pwd, record_login_failure, record_login_success
from db.database import db

router = APIRouter()


class LoginRequest(BaseModel):
    pwd: str


class ImportRequest(BaseModel):
    codes: List[str] = []


class CodeRequest(BaseModel):
    code: str = ""


class UserResetRequest(BaseModel):
    openid: str = ""


class UserBatchResetRequest(BaseModel):
    openids: List[str] = []


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
def get_stats(request: Request):
    require_admin(request)

    with db() as conn:
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

    return {
        "total": total,
        "used": used,
        "unused": unused,
        "users_count": users_count,
        "messages_count": messages_count,
        "messages": messages,
        "records": records,
        "token_configured": bool(config.WECHAT_TOKEN),
        "website": config.WEBSITE_URL
    }


@router.post("/api/import")
def import_codes(req: ImportRequest, request: Request):
    require_admin(request)

    added = 0
    duplicates = []
    seen = set()
    with db() as conn:
        cursor = conn.cursor()
        for code in req.codes:
            c = code.strip() if isinstance(code, str) else ""
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
    return {"status": "success", "added": added, "duplicates": duplicates, "total": added + len(duplicates)}


def _reset_code_by_value(cursor, code: str) -> bool:
    cursor.execute("SELECT status FROM codes WHERE code = ?", (code,))
    row = cursor.fetchone()
    if row is None or row["status"] != "assigned":
        return row is not None
    cursor.execute(
        "UPDATE codes SET status = 'unused', assigned_openid = NULL, assigned_at = NULL WHERE code = ?",
        (code,)
    )
    cursor.execute("DELETE FROM users WHERE code = ?", (code,))
    return True


@router.post("/api/codes/reset")
def reset_code(req: CodeRequest, request: Request):
    require_admin(request)
    code = (req.code or "").strip()
    if not code:
        raise HTTPException(status_code=400, detail="激活码不能为空")

    with db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM codes WHERE code = ?", (code,))
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="激活码不存在")
        if row["status"] != "assigned":
            return {"status": "success", "reset": False, "message": "该激活码未被领取，无需重置"}

        _reset_code_by_value(cursor, code)
        conn.commit()
    return {"status": "success", "reset": True, "message": "已重置为待领取，原领取人可重新领取"}


@router.post("/api/codes/delete")
def delete_code(req: CodeRequest, request: Request):
    require_admin(request)
    code = (req.code or "").strip()
    if not code:
        raise HTTPException(status_code=400, detail="激活码不能为空")

    with db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM codes WHERE code = ?", (code,))
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="激活码不存在")

        was_assigned = row["status"] == "assigned"
        cursor.execute("DELETE FROM codes WHERE code = ?", (code,))
        cursor.execute("DELETE FROM users WHERE code = ?", (code,))
        conn.commit()
    return {"status": "success", "message": "已删除" + ("（原领取人绑定已解除）" if was_assigned else "")}


@router.post("/api/codes/delete-unused")
def delete_unused_codes(request: Request):
    require_admin(request)
    with db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as n FROM codes WHERE status = 'unused'")
        n = cursor.fetchone()["n"]
        cursor.execute("DELETE FROM codes WHERE status = 'unused'")
        conn.commit()
    return {"status": "success", "deleted": n, "message": f"已清空 {n} 个未使用激活码"}


@router.get("/api/users")
def list_users(request: Request):
    require_admin(request)
    with db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM users")
        total = cursor.fetchone()["total"]
        cursor.execute("SELECT openid, code, created_at FROM users ORDER BY id DESC LIMIT 500")
        users = [dict(r) for r in cursor.fetchall()]
    return {"status": "success", "total": total, "users": users}


def _reset_user_by_openid(cursor, openid: str):
    """收回指定用户的激活码。返回 (ok, code)。"""
    cursor.execute("SELECT code FROM users WHERE openid = ?", (openid,))
    row = cursor.fetchone()
    if row is None:
        return False, ""
    code = row["code"]
    cursor.execute(
        "UPDATE codes SET status = 'unused', assigned_openid = NULL, assigned_at = NULL WHERE code = ?",
        (code,)
    )
    cursor.execute("DELETE FROM users WHERE openid = ?", (openid,))
    return True, code


@router.post("/api/users/reset")
def reset_user(req: UserResetRequest, request: Request):
    require_admin(request)
    openid = (req.openid or "").strip()
    if not openid:
        raise HTTPException(status_code=400, detail="OpenID 不能为空")

    with db() as conn:
        cursor = conn.cursor()
        ok, code = _reset_user_by_openid(cursor, openid)
        if not ok:
            raise HTTPException(status_code=404, detail="该用户尚未领取激活码")
        conn.commit()
    return {"status": "success", "reset": True, "code": code, "message": f"已收回 {openid} 的激活码，其可重新领取"}


@router.post("/api/users/reset-batch")
def reset_users_batch(req: UserBatchResetRequest, request: Request):
    require_admin(request)
    openids = [o.strip() for o in (req.openids or []) if o and o.strip()]
    if not openids:
        raise HTTPException(status_code=400, detail="请选择要重置的用户")

    with db() as conn:
        cursor = conn.cursor()
        reset, not_found = [], []
        for openid in dict.fromkeys(openids):
            ok, _ = _reset_user_by_openid(cursor, openid)
            (reset if ok else not_found).append(openid)
        conn.commit()
    return {"status": "success", "reset": reset, "not_found": not_found,
            "message": f"已重置 {len(reset)} 人" + (f"，{len(not_found)} 人无码可收" if not_found else "")}
