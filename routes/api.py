from typing import List

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

import config
from core.auth import bearer_token, issue_token, require_admin, revoke_token
from core.security import check_rate_limit, get_client_ip, is_valid_pwd, record_login_failure, record_login_success
from core.rules import get_setting, list_all_rules, set_setting
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


class RuleRequest(BaseModel):
    keyword: str = ""
    mode: str = "contains"
    action: str = "none"
    content: str = ""
    priority: int = 100
    enabled: bool = True


class SettingsRequest(BaseModel):
    settings: dict = {}


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
    if len(req.codes) > 2000:
        raise HTTPException(status_code=400, detail="单次最多导入 2000 个")

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
def list_users(request: Request, q: str = "", limit: int = 100, offset: int = 0):
    require_admin(request)
    limit = max(1, min(limit, 500))
    offset = max(0, offset)
    with db() as conn:
        cursor = conn.cursor()
        if q.strip():
            like = f"%{q.strip()}%"
            cursor.execute("SELECT COUNT(*) as total FROM users WHERE openid LIKE ? OR code LIKE ?", (like, like))
            total = cursor.fetchone()["total"]
            cursor.execute(
                "SELECT openid, code, created_at FROM users WHERE openid LIKE ? OR code LIKE ? "
                "ORDER BY id DESC LIMIT ? OFFSET ?", (like, like, limit, offset))
        else:
            cursor.execute("SELECT COUNT(*) as total FROM users")
            total = cursor.fetchone()["total"]
            cursor.execute(
                "SELECT openid, code, created_at FROM users ORDER BY id DESC LIMIT ? OFFSET ?",
                (limit, offset))
        users = [dict(r) for r in cursor.fetchall()]
    return {"status": "success", "total": total, "users": users}


@router.get("/api/codes")
def list_codes(request: Request, q: str = "", status: str = "", limit: int = 100, offset: int = 0):
    require_admin(request)
    limit = max(1, min(limit, 500))
    offset = max(0, offset)
    conds, params = [], []
    if status in ("unused", "assigned"):
        conds.append("status = ?")
        params.append(status)
    if q.strip():
        conds.append("(code LIKE ? OR assigned_openid LIKE ?)")
        like = f"%{q.strip()}%"
        params.extend([like, like])
    where = ("WHERE " + " AND ".join(conds)) if conds else ""
    with db() as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) as total FROM codes {where}", params)
        total = cursor.fetchone()["total"]
        cursor.execute(
            f"SELECT id, code, status, assigned_openid, assigned_at, created_at FROM codes "
            f"{where} ORDER BY id DESC LIMIT ? OFFSET ?", (*params, limit, offset))
        records = [dict(r) for r in cursor.fetchall()]
    return {"status": "success", "total": total, "codes": records}


@router.get("/api/messages")
def list_messages(request: Request, q: str = "", limit: int = 100, offset: int = 0):
    require_admin(request)
    limit = max(1, min(limit, 500))
    offset = max(0, offset)
    with db() as conn:
        cursor = conn.cursor()
        if q.strip():
            like = f"%{q.strip()}%"
            cursor.execute("SELECT COUNT(*) as total FROM messages WHERE openid LIKE ? OR content LIKE ?", (like, like))
            total = cursor.fetchone()["total"]
            cursor.execute(
                "SELECT * FROM messages WHERE openid LIKE ? OR content LIKE ? "
                "ORDER BY id DESC LIMIT ? OFFSET ?", (like, like, limit, offset))
        else:
            cursor.execute("SELECT COUNT(*) as total FROM messages")
            total = cursor.fetchone()["total"]
            cursor.execute("SELECT * FROM messages ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset))
        messages = [dict(r) for r in cursor.fetchall()]
    return {"status": "success", "total": total, "messages": messages}


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


def _check_rule(req: RuleRequest):
    kw = (req.keyword or "").strip()
    if not kw:
        raise HTTPException(status_code=400, detail="关键词不能为空")
    if req.mode not in ("contains", "exact"):
        raise HTTPException(status_code=400, detail="匹配模式只能是 contains / exact")
    if req.action not in ("none", "code"):
        raise HTTPException(status_code=400, detail="动作只能是 none / code")
    return kw


@router.get("/api/rules")
def list_rules(request: Request):
    require_admin(request)
    return {"status": "success", "rules": list_all_rules()}


@router.post("/api/rules")
def create_rule(req: RuleRequest, request: Request):
    require_admin(request)
    kw = _check_rule(req)
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO keyword_rules (keyword, mode, action, content, priority, enabled) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (kw, req.mode, req.action, req.content or "", int(req.priority), 1 if req.enabled else 0),
        )
        conn.commit()
        rule_id = cur.lastrowid
    return {"status": "success", "id": rule_id}


@router.put("/api/rules/{rule_id}")
def update_rule(rule_id: int, req: RuleRequest, request: Request):
    require_admin(request)
    kw = _check_rule(req)
    with db() as conn:
        cur = conn.execute(
            "UPDATE keyword_rules SET keyword = ?, mode = ?, action = ?, content = ?, "
            "priority = ?, enabled = ? WHERE id = ?",
            (kw, req.mode, req.action, req.content or "", int(req.priority), 1 if req.enabled else 0, rule_id),
        )
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="规则不存在")
    return {"status": "success"}


@router.delete("/api/rules/{rule_id}")
def delete_rule(rule_id: int, request: Request):
    require_admin(request)
    with db() as conn:
        cur = conn.execute("DELETE FROM keyword_rules WHERE id = ?", (rule_id,))
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="规则不存在")
    return {"status": "success"}


@router.get("/api/settings")
def get_settings(request: Request):
    require_admin(request)
    keys = ["welcome_reply", "fallback_reply", "repeat_reply", "new_reply", "empty_reply", "group_id"]
    return {"status": "success", "settings": {k: get_setting(k) for k in keys}}


@router.put("/api/settings")
def update_settings(req: SettingsRequest, request: Request):
    require_admin(request)
    allowed = {"welcome_reply", "fallback_reply", "repeat_reply", "new_reply", "empty_reply", "group_id"}
    updated = []
    for k, v in (req.settings or {}).items():
        if k in allowed and isinstance(v, str):
            set_setting(k, v)
            updated.append(k)
    return {"status": "success", "updated": updated}
