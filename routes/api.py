from typing import Any, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

import config
import core.config_store as cs
from core.auth import bearer_token, issue_token, require_admin, revoke_all_tokens, revoke_token
from core.security import check_rate_limit, escape_like, get_client_ip, is_valid_pwd, record_login_failure, record_login_success
from core.rules import delete_custom_variable, get_setting, list_all_rules, list_custom_variables, set_custom_variable, set_setting
from db.database import db

router = APIRouter()


class SetupRequest(BaseModel):
    admin_password: str
    wechat_token: str = ""
    website_url: str = ""
    group_id: str = ""


class ConfigUpdateRequest(BaseModel):
    wechat_token: Optional[str] = None
    website_url: Optional[str] = None
    group_id: Optional[str] = None
    new_admin_password: Optional[str] = None


class LoginRequest(BaseModel):
    pwd: str


class ImportRequest(BaseModel):
    pool_id: Optional[int] = 1
    codes: List[str] = []
    multi_pool_codes: Optional[dict[str, List[str]]] = None


class PoolCreateRequest(BaseModel):
    name: str
    key: str
    description: str = ""


class PoolUpdateRequest(BaseModel):
    name: str
    description: str = ""


class CodeRequest(BaseModel):
    code: str = ""


class UserResetRequest(BaseModel):
    openid: str = ""


class UserBatchResetRequest(BaseModel):
    openids: List[str] = []


class VariableCreateRequest(BaseModel):
    key: str
    value: str
    description: Optional[str] = ""


class VariableUpdateRequest(BaseModel):
    value: str
    description: Optional[str] = ""


class RuleRequest(BaseModel):
    keyword: str = ""
    mode: str = "contains"
    action: str = "none"
    content: str = ""
    priority: int = 100
    enabled: bool = True
    recipe: Optional[str] = ""
    status_replies: Optional[Any] = None
    start_time: Optional[str] = ""
    end_time: Optional[str] = ""


class RuleBatchDeleteRequest(BaseModel):
    ids: List[int] = []


class RuleBatchToggleRequest(BaseModel):
    ids: List[int] = []
    enabled: bool


class RuleImportItem(BaseModel):
    keyword: str
    mode: str = "contains"
    action: str = "none"
    content: str = ""
    priority: int = 100
    enabled: bool = True
    recipe: str = ""
    status_replies: Optional[Any] = None
    start_time: Optional[str] = ""
    end_time: Optional[str] = ""


class RuleBatchImportRequest(BaseModel):
    mode: str = "skip"  # 'skip' | 'overwrite'
    rules: List[RuleImportItem] = []


class SettingsRequest(BaseModel):
    settings: dict = {}


@router.get("/api/setup/status")
def setup_status():
    """公开接口：获取系统初始化及微信 Token 配置状态，供前端路由守卫使用。"""
    return {
        "status": "success",
        "setup_done": cs.is_setup_done(),
        "wechat_configured": cs.is_wechat_configured(),
    }


@router.post("/api/setup")
def setup_initial(req: SetupRequest, request: Request):
    """公开接口：系统未初始化时进行首发配置，设置管理密码和可选的微信Token。"""
    ip = get_client_ip(request)
    check_rate_limit(ip)

    if cs.is_setup_done():
        record_login_failure(ip)
        raise HTTPException(status_code=403, detail="系统已完成初始化，禁止重复设置")

    pwd = (req.admin_password or "").strip()
    if len(pwd) < 8:
        raise HTTPException(status_code=400, detail="管理员密码长度至少为 8 位")

    cs.set_admin_password(pwd)

    if req.wechat_token:
        token = req.wechat_token.strip()
        if len(token) > 128:
            raise HTTPException(status_code=400, detail="微信 Token 长度不能超过 128 位")
        if not cs.is_wechat_token_from_env():
            cs.set_setting("wechat_token", token)

    if req.website_url:
        url = req.website_url.strip()
        if len(url) > 256 or not (url.startswith("http://") or url.startswith("https://")):
            raise HTTPException(status_code=400, detail="兑换网站地址必须以 http:// 或 https:// 开头且不超过 256 字")
        if not cs.is_website_url_from_env():
            cs.set_setting("website_url", url)
            set_custom_variable("site", url, "兑换网站地址")

    if req.group_id:
        gid = req.group_id.strip()
        if len(gid) > 64:
            raise HTTPException(status_code=400, detail="群入口微信号长度不能超过 64 字")
        if not cs.is_group_id_from_env():
            cs.set_setting("group_id", gid)
            set_custom_variable("group", gid, "微信群/客服入口微信号")

    record_login_success(ip)
    token, expires_at = issue_token()
    return {"status": "success", "token": token, "expires_at": expires_at, "message": "初始化设置成功"}


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


@router.post("/api/logout-all")
def logout_all(request: Request):
    require_admin(request)
    revoke_all_tokens()
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

        cursor.execute("SELECT id, code, status, assigned_openid, assigned_at, created_at FROM codes ORDER BY id DESC LIMIT 500")
        records = [dict(r) for r in cursor.fetchall()]

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


@router.get("/api/pools")
def list_pools(request: Request):
    require_admin(request)
    with db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.id, p.name, p.key, p.description, p.is_default, p.created_at,
                   COUNT(c.id) as total,
                   SUM(CASE WHEN c.status = 'assigned' THEN 1 ELSE 0 END) as used,
                   SUM(CASE WHEN c.status = 'unused' THEN 1 ELSE 0 END) as unused
            FROM code_pools p
            LEFT JOIN codes c ON p.id = c.pool_id
            GROUP BY p.id
            ORDER BY p.id ASC
        """)
        pools = [dict(r) for r in cursor.fetchall()]
        for p in pools:
            p["total"] = p["total"] or 0
            p["used"] = p["used"] or 0
            p["unused"] = p["unused"] or 0
            p["is_default"] = bool(p.get("is_default"))
    return {"status": "success", "pools": pools}


@router.post("/api/pools/{pool_id}/set-default")
def set_default_pool(pool_id: int, request: Request):
    require_admin(request)
    with db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM code_pools WHERE id = ?", (pool_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="卡池不存在")
        cursor.execute("UPDATE code_pools SET is_default = 0")
        cursor.execute("UPDATE code_pools SET is_default = 1 WHERE id = ?", (pool_id,))
        conn.commit()
    return {"status": "success", "message": "已成功设置为主卡池，{code} 占位符将绑定此卡池"}


@router.post("/api/pools")
def create_pool(req: PoolCreateRequest, request: Request):
    require_admin(request)
    name = (req.name or "").strip()
    key = (req.key or "").strip().lower()
    desc = (req.description or "").strip()
    if not name or len(name) > 64:
        raise HTTPException(status_code=400, detail="卡池名称不能为空且最多 64 字")
    import re
    if not re.match(r"^[a-z0-9_]{1,32}$", key):
        raise HTTPException(status_code=400, detail="卡池标识 key 只能由 1~32 位小写字母、数字和下划线组成")

    with db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM code_pools WHERE key = ?", (key,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail=f"卡池标识 key '{key}' 已存在")
        cursor.execute(
            "INSERT INTO code_pools (name, key, description) VALUES (?, ?, ?)",
            (name, key, desc),
        )
        conn.commit()
        pool_id = cursor.lastrowid
    return {"status": "success", "id": pool_id}


@router.put("/api/pools/{pool_id}")
def update_pool(pool_id: int, req: PoolUpdateRequest, request: Request):
    require_admin(request)
    name = (req.name or "").strip()
    desc = (req.description or "").strip()
    if not name or len(name) > 64:
        raise HTTPException(status_code=400, detail="卡池名称不能为空且最多 64 字")

    with db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE code_pools SET name = ?, description = ? WHERE id = ?",
            (name, desc, pool_id),
        )
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="卡池不存在")
    return {"status": "success"}


@router.delete("/api/pools/{pool_id}")
def delete_pool(pool_id: int, request: Request):
    require_admin(request)
    if pool_id == 1:
        raise HTTPException(status_code=400, detail="默认卡券池禁止删除")

    with db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM code_pools WHERE id = ?", (pool_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="卡池不存在")
        cursor.execute("SELECT COUNT(*) as n FROM codes WHERE pool_id = ?", (pool_id,))
        if cursor.fetchone()["n"] > 0:
            raise HTTPException(status_code=400, detail="该卡池内尚有激活码，请先清空或删除激活码后再删除卡池")
        cursor.execute("DELETE FROM code_pools WHERE id = ?", (pool_id,))
        conn.commit()
    return {"status": "success"}


@router.post("/api/import")
def import_codes(req: ImportRequest, request: Request):
    require_admin(request)
    added = 0
    duplicates = []
    by_pool = {}

    with db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, key FROM code_pools")
        pool_map = {r["key"]: r["id"] for r in cursor.fetchall()}
        id_to_key = {v: k for k, v in pool_map.items()}

        # 1. 多品类字典导入
        if req.multi_pool_codes:
            total_items = sum(len(codes) for codes in req.multi_pool_codes.values())
            if total_items > 2000:
                raise HTTPException(status_code=400, detail="单次最多导入 2000 个激活码")

            for p_key, code_list in req.multi_pool_codes.items():
                p_key_clean = (p_key or "").strip().lower()
                if p_key_clean not in pool_map:
                    raise HTTPException(status_code=400, detail=f"未识别的卡池 key: '{p_key}'，请先创建对应卡池")
                target_pool_id = pool_map[p_key_clean]
                pool_added = 0
                seen = set()

                for raw_code in code_list:
                    c = raw_code.strip() if isinstance(raw_code, str) else ""
                    if not c or c in seen:
                        if c:
                            duplicates.append(c)
                        continue
                    if len(c) > 128:
                        raise HTTPException(status_code=400, detail="单个激活码最多 128 字")
                    seen.add(c)
                    cursor.execute("SELECT id FROM codes WHERE code = ?", (c,))
                    if cursor.fetchone():
                        duplicates.append(c)
                        continue
                    try:
                        cursor.execute(
                            "INSERT INTO codes (code, pool_id, status) VALUES (?, ?, 'unused')",
                            (c, target_pool_id),
                        )
                        pool_added += 1
                        added += 1
                    except Exception:
                        duplicates.append(c)
                by_pool[p_key_clean] = pool_added
            conn.commit()
            return {"status": "success", "added": added, "duplicates": duplicates, "total": added + len(duplicates), "by_pool": by_pool}

        # 2. 单池或默认池列表导入
        if len(req.codes) > 2000:
            raise HTTPException(status_code=400, detail="单次最多导入 2000 个")
        target_pool_id = req.pool_id or 1
        if target_pool_id not in id_to_key:
            cursor.execute("SELECT id FROM code_pools WHERE id = ?", (target_pool_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=400, detail="目标卡池不存在")

        target_key = id_to_key.get(target_pool_id, str(target_pool_id))
        seen = set()
        for code in req.codes:
            c = code.strip() if isinstance(code, str) else ""
            if not c or c in seen:
                if c:
                    duplicates.append(c)
                continue
            if len(c) > 128:
                raise HTTPException(status_code=400, detail="单个激活码最多 128 字")
            seen.add(c)
            cursor.execute("SELECT id FROM codes WHERE code = ?", (c,))
            if cursor.fetchone():
                duplicates.append(c)
                continue
            try:
                cursor.execute(
                    "INSERT INTO codes (code, pool_id, status) VALUES (?, ?, 'unused')",
                    (c, target_pool_id),
                )
                added += 1
            except Exception:
                duplicates.append(c)
        by_pool[target_key] = added
        conn.commit()
    return {"status": "success", "added": added, "duplicates": duplicates, "total": added + len(duplicates), "by_pool": by_pool}


def _reset_code_by_value(cursor, code: str) -> bool:
    cursor.execute("SELECT status FROM codes WHERE code = ?", (code,))
    row = cursor.fetchone()
    if row is None or row["status"] != "assigned":
        return row is not None
    cursor.execute(
        "UPDATE codes SET status = 'unused', assigned_openid = NULL, assigned_at = NULL WHERE code = ?",
        (code,)
    )
    cursor.execute("DELETE FROM user_code_claims WHERE code = ?", (code,))
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
        cursor.execute("DELETE FROM user_code_claims WHERE code = ?", (code,))
        cursor.execute("DELETE FROM users WHERE code = ?", (code,))
        conn.commit()
    return {"status": "success", "message": "已删除" + ("（原领取人绑定已解除）" if was_assigned else "")}


@router.post("/api/codes/delete-unused")
def delete_unused_codes(request: Request, pool_id: Optional[int] = None):
    require_admin(request)
    with db() as conn:
        cursor = conn.cursor()
        if pool_id is not None and pool_id > 0:
            cursor.execute("SELECT COUNT(*) as n FROM codes WHERE status = 'unused' AND pool_id = ?", (pool_id,))
            n = cursor.fetchone()["n"]
            cursor.execute("DELETE FROM codes WHERE status = 'unused' AND pool_id = ?", (pool_id,))
        else:
            cursor.execute("SELECT COUNT(*) as n FROM codes WHERE status = 'unused'")
            n = cursor.fetchone()["n"]
            cursor.execute("DELETE FROM codes WHERE status = 'unused'")
        conn.commit()
    return {"status": "success", "deleted": n, "message": f"已清空 {n} 个未使用激活码"}


@router.get("/api/users")
def list_users(request: Request, q: str = "", status: str = "", limit: int = 100, offset: int = 0):
    require_admin(request)
    limit = max(1, min(limit, 500))
    offset = max(0, offset)
    conds, params = [], []
    if status in ("subscribe", "unsubscribe"):
        conds.append("u.last_event = ?")
        params.append(status)
    if q.strip():
        conds.append("""(
            u.openid LIKE ? ESCAPE '\\' 
            OR u.code LIKE ? ESCAPE '\\' 
            OR u.openid IN (SELECT openid FROM user_code_claims WHERE code LIKE ? ESCAPE '\\')
        )""")
        like = f"%{escape_like(q.strip())}%"
        params.extend([like, like, like])
    where = ("WHERE " + " AND ".join(conds)) if conds else ""
    with db() as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) as total FROM users u {where}", params)
        total = cursor.fetchone()["total"]
        cursor.execute(
            f"SELECT u.openid, u.code, u.last_event, u.created_at FROM users u {where} "
            f"ORDER BY u.id DESC LIMIT ? OFFSET ?", (*params, limit, offset))
        users = [dict(r) for r in cursor.fetchall()]

        if users:
            openids = [u["openid"] for u in users]
            placeholders = ",".join("?" for _ in openids)
            cursor.execute(f"""
                SELECT ucc.openid, ucc.code, ucc.pool_id, p.name as pool_name, p.key as pool_key
                FROM user_code_claims ucc
                LEFT JOIN code_pools p ON ucc.pool_id = p.id
                WHERE ucc.openid IN ({placeholders})
                ORDER BY ucc.id ASC
            """, openids)
            claims_rows = cursor.fetchall()

            user_claims_map = {}
            for row in claims_rows:
                user_claims_map.setdefault(row["openid"], []).append({
                    "code": row["code"],
                    "pool_id": row["pool_id"],
                    "pool_name": row["pool_name"] or "默认池",
                    "pool_key": row["pool_key"] or "default"
                })

            for u in users:
                c_list = user_claims_map.get(u["openid"], [])
                if not c_list and u.get("code"):
                    c_list = [{
                        "code": u["code"],
                        "pool_id": 1,
                        "pool_name": "默认池",
                        "pool_key": "default"
                    }]
                u["claims"] = c_list
                u["codes"] = [item["code"] for item in c_list]
                u["total_codes"] = len(c_list)
    return {"status": "success", "total": total, "users": users}


@router.get("/api/codes")
def list_codes(request: Request, q: str = "", status: str = "", pool_id: Optional[int] = None, limit: int = 100, offset: int = 0):
    require_admin(request)
    limit = max(1, min(limit, 500))
    offset = max(0, offset)
    conds, params = [], []
    if status in ("unused", "assigned"):
        conds.append("c.status = ?")
        params.append(status)
    if pool_id is not None and pool_id > 0:
        conds.append("c.pool_id = ?")
        params.append(pool_id)
    if q.strip():
        conds.append("(c.code LIKE ? ESCAPE '\\' OR c.assigned_openid LIKE ? ESCAPE '\\')")
        like = f"%{escape_like(q.strip())}%"
        params.extend([like, like])
    where = ("WHERE " + " AND ".join(conds)) if conds else ""
    with db() as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) as total FROM codes c {where}", params)
        total = cursor.fetchone()["total"]
        cursor.execute(
            f"SELECT c.id, c.code, c.pool_id, p.name as pool_name, p.key as pool_key, "
            f"c.status, c.assigned_openid, c.assigned_at, c.created_at "
            f"FROM codes c LEFT JOIN code_pools p ON c.pool_id = p.id "
            f"{where} ORDER BY c.id DESC LIMIT ? OFFSET ?", (*params, limit, offset))
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
            like = f"%{escape_like(q.strip())}%"
            cursor.execute(
                "SELECT COUNT(*) as total FROM messages WHERE openid LIKE ? ESCAPE '\\' OR content LIKE ? ESCAPE '\\' OR reply_content LIKE ? ESCAPE '\\'",
                (like, like, like)
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
    return {"status": "success", "total": total, "messages": messages}


def _reset_user_by_openid(cursor, openid: str):
    """收回指定用户的激活码。返回 (ok, list_of_codes)。"""
    cursor.execute("SELECT code FROM user_code_claims WHERE openid = ?", (openid,))
    claim_rows = cursor.fetchall()
    codes = [r["code"] for r in claim_rows]

    # 兼容老数据（claims 暂未镜像时回退查 users）
    if not codes:
        cursor.execute("SELECT code FROM users WHERE openid = ?", (openid,))
        u_row = cursor.fetchone()
        if u_row and u_row["code"]:
            codes = [u_row["code"]]

    if not codes:
        return False, []

    for code in codes:
        cursor.execute(
            "UPDATE codes SET status = 'unused', assigned_openid = NULL, assigned_at = NULL WHERE code = ?",
            (code,)
        )
    cursor.execute("DELETE FROM user_code_claims WHERE openid = ?", (openid,))
    cursor.execute("DELETE FROM users WHERE openid = ?", (openid,))
    return True, codes


@router.post("/api/users/reset")
def reset_user(req: UserResetRequest, request: Request):
    require_admin(request)
    openid = (req.openid or "").strip()
    if not openid:
        raise HTTPException(status_code=400, detail="OpenID 不能为空")

    with db() as conn:
        cursor = conn.cursor()
        ok, codes = _reset_user_by_openid(cursor, openid)
        if not ok:
            raise HTTPException(status_code=404, detail="该用户尚未领取激活码")
        conn.commit()
    code_str = ", ".join(codes) if codes else ""
    return {"status": "success", "reset": True, "code": code_str, "codes": codes, "message": f"已收回 {openid} 的激活码，其可重新领取"}


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


def _serialize_status_replies(val: Any) -> str:
    if val is None:
        return ""
    if isinstance(val, str):
        return val
    try:
        import json
        return json.dumps(val, ensure_ascii=False)
    except Exception:
        return ""


def _check_rule(req: RuleRequest):
    kw = (req.keyword or "").strip()
    action = (req.action or "none").strip()
    if action in ("event_subscribe", "event_fallback"):
        if not kw:
            kw = f"__{action}__"
    else:
        if not kw:
            raise HTTPException(status_code=400, detail="关键词不能为空")
        if len(kw) > 128:
            raise HTTPException(status_code=400, detail="关键词最多 128 字")

    if req.mode not in ("contains", "exact", "regex"):
        raise HTTPException(status_code=400, detail="匹配模式只能是 contains / exact / regex")

    if req.mode == "regex" and not action.startswith("event_"):
        import re
        try:
            re.compile(kw)
        except re.error as e:
            raise HTTPException(status_code=400, detail=f"正则表达式语法错误: {str(e)}")

    if action not in ("none", "code", "event_subscribe", "event_fallback"):
        raise HTTPException(status_code=400, detail="动作只能是 none / code / event_subscribe / event_fallback")

    if len(req.content or "") > 2000:
        raise HTTPException(status_code=400, detail="回复内容最多 2000 字")
    req.priority = max(0, min(int(req.priority or 0), 10000))
    return kw


@router.get("/api/variables")
def get_variables(request: Request):
    require_admin(request)
    return {"status": "success", "variables": list_custom_variables()}


@router.post("/api/variables")
def create_variable(req: VariableCreateRequest, request: Request):
    require_admin(request)
    k = (req.key or "").strip().lower()
    if not k or len(k) > 32:
        raise HTTPException(status_code=400, detail="变量标识 key 不能为空且最多 32 字")
    import re
    if not re.match(r"^[a-zA-Z0-9_]{1,32}$", k):
        raise HTTPException(status_code=400, detail="变量标识 key 只能由字母、数字和下划线组成")
    var_id = set_custom_variable(k, req.value or "", req.description or "")
    return {"status": "success", "id": var_id}


@router.put("/api/variables/{var_id}")
def update_variable(var_id: int, req: VariableUpdateRequest, request: Request):
    require_admin(request)
    with db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, key FROM custom_variables WHERE id = ?", (var_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="变量不存在")
        cursor.execute(
            "UPDATE custom_variables SET value = ?, description = ? WHERE id = ?",
            (req.value or "", req.description or "", var_id),
        )
        conn.commit()
    return {"status": "success"}


@router.delete("/api/variables/{var_id}")
def remove_variable(var_id: int, request: Request):
    require_admin(request)
    with db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, key FROM custom_variables WHERE id = ?", (var_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="变量不存在")
        if row["key"] in ("site", "group"):
            raise HTTPException(status_code=400, detail="系统核心内置变量（site, group）禁止删除，可在列表中直接修改其内容")
        cursor.execute("DELETE FROM custom_variables WHERE id = ?", (var_id,))
        conn.commit()
    return {"status": "success"}


@router.get("/api/rules")
def list_rules(request: Request):
    require_admin(request)
    return {"status": "success", "rules": list_all_rules()}


@router.post("/api/rules")
def create_rule(req: RuleRequest, request: Request):
    require_admin(request)
    kw = _check_rule(req)
    sr_str = _serialize_status_replies(req.status_replies)
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO keyword_rules (keyword, mode, action, content, priority, enabled, recipe, status_replies, start_time, end_time) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (kw, req.mode, req.action, req.content or "", int(req.priority), 1 if req.enabled else 0, req.recipe or "", sr_str, req.start_time or "", req.end_time or ""),
        )
        conn.commit()
        rule_id = cur.lastrowid
    return {"status": "success", "id": rule_id}


@router.put("/api/rules/{rule_id}")
def update_rule(rule_id: int, req: RuleRequest, request: Request):
    require_admin(request)
    kw = _check_rule(req)
    sr_str = _serialize_status_replies(req.status_replies)
    with db() as conn:
        cur = conn.execute(
            "UPDATE keyword_rules SET keyword = ?, mode = ?, action = ?, content = ?, "
            "priority = ?, enabled = ?, recipe = ?, status_replies = ?, start_time = ?, end_time = ? WHERE id = ?",
            (kw, req.mode, req.action, req.content or "", int(req.priority), 1 if req.enabled else 0, req.recipe or "", sr_str, req.start_time or "", req.end_time or "", rule_id),
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


@router.post("/api/rules/batch-delete")
def batch_delete_rules(req: RuleBatchDeleteRequest, request: Request):
    require_admin(request)
    ids = [int(i) for i in (req.ids or []) if i > 0]
    if not ids:
        raise HTTPException(status_code=400, detail="请选择要删除的规则")
    with db() as conn:
        placeholders = ",".join("?" for _ in ids)
        cur = conn.execute(f"DELETE FROM keyword_rules WHERE id IN ({placeholders})", ids)
        conn.commit()
        count = cur.rowcount
    return {"status": "success", "deleted": count}


@router.post("/api/rules/batch-toggle")
def batch_toggle_rules(req: RuleBatchToggleRequest, request: Request):
    require_admin(request)
    ids = [int(i) for i in (req.ids or []) if i > 0]
    if not ids:
        raise HTTPException(status_code=400, detail="请选择要操作的规则")
    val = 1 if req.enabled else 0
    with db() as conn:
        placeholders = ",".join("?" for _ in ids)
        cur = conn.execute(f"UPDATE keyword_rules SET enabled = ? WHERE id IN ({placeholders})", [val, *ids])
        conn.commit()
        count = cur.rowcount
    return {"status": "success", "updated": count}


@router.post("/api/rules/batch-import")
def batch_import_rules(req: RuleBatchImportRequest, request: Request):
    require_admin(request)
    if len(req.rules) > 500:
        raise HTTPException(status_code=400, detail="单次最多导入 500 条规则")
    if req.mode not in ("skip", "overwrite"):
        raise HTTPException(status_code=400, detail="导入模式只能是 skip 或 overwrite")

    added = 0
    updated = 0
    skipped = 0

    with db() as conn:
        cursor = conn.cursor()
        for item in req.rules:
            kw = (item.keyword or "").strip()
            if not kw or len(kw) > 128:
                continue
            mode = item.mode if item.mode in ("contains", "exact", "regex") else "contains"
            action = item.action if item.action in ("none", "code", "event_subscribe", "event_fallback") else "none"
            content = (item.content or "")[:2000]
            priority = max(0, min(int(item.priority or 100), 10000))
            enabled = 1 if item.enabled else 0
            recipe = item.recipe or ""
            sr_str = _serialize_status_replies(item.status_replies)
            st_str = item.start_time or ""
            et_str = item.end_time or ""

            cursor.execute("SELECT id FROM keyword_rules WHERE keyword = ? AND mode = ?", (kw, mode))
            existing = cursor.fetchone()
            if existing:
                if req.mode == "overwrite":
                    cursor.execute("""
                        UPDATE keyword_rules SET action = ?, content = ?, priority = ?, enabled = ?, recipe = ?,
                               status_replies = ?, start_time = ?, end_time = ?
                        WHERE id = ?
                    """, (action, content, priority, enabled, recipe, sr_str, st_str, et_str, existing["id"]))
                    updated += 1
                else:
                    skipped += 1
            else:
                cursor.execute("""
                    INSERT INTO keyword_rules (keyword, mode, action, content, priority, enabled, recipe, status_replies, start_time, end_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (kw, mode, action, content, priority, enabled, recipe, sr_str, st_str, et_str))
                added += 1
        conn.commit()

    return {"status": "success", "added": added, "updated": updated, "skipped": skipped, "total": added + updated + skipped}


@router.get("/api/settings")
def get_settings(request: Request):
    require_admin(request)
    keys = ["welcome_reply", "fallback_reply", "new_reply", "empty_reply", "group_id"]
    return {"status": "success", "settings": {k: get_setting(k) for k in keys}}


@router.put("/api/settings")
def update_settings(req: SettingsRequest, request: Request):
    require_admin(request)
    allowed = {"welcome_reply", "fallback_reply", "new_reply", "empty_reply", "group_id"}
    updated = []
    for k, v in (req.settings or {}).items():
        if k in allowed and isinstance(v, str) and len(v) <= 2000:
            set_setting(k, v)
            updated.append(k)
    return {"status": "success", "updated": updated}


@router.get("/api/config")
def get_system_config(request: Request):
    require_admin(request)
    current_token = cs.get_wechat_token()
    return {
        "status": "success",
        "config": {
            "wechat_token": {
                "masked_value": cs.mask_token(current_token),
                "is_set": bool(current_token),
                "from_env": cs.is_wechat_token_from_env(),
                "editable": not cs.is_wechat_token_from_env(),
            },
            "website_url": {
                "value": cs.get_website_url(),
                "from_env": cs.is_website_url_from_env(),
                "editable": not cs.is_website_url_from_env(),
            },
            "group_id": {
                "value": cs.get_group_id(),
                "from_env": cs.is_group_id_from_env(),
                "editable": not cs.is_group_id_from_env(),
            },
            "admin_password": {
                "has_env": bool(config.ADMIN_PASSWORDS),
                "has_db": cs.has_db_admin_password(),
                "editable": True,
            },
        },
    }


@router.put("/api/config")
def update_system_config(req: ConfigUpdateRequest, request: Request):
    require_admin(request)

    if req.wechat_token is not None:
        if cs.is_wechat_token_from_env():
            raise HTTPException(status_code=400, detail="微信 Token 由环境变量托管，禁止在网页后台修改")
        token = req.wechat_token.strip()
        if len(token) > 128:
            raise HTTPException(status_code=400, detail="微信 Token 长度不能超过 128 位")
        cs.set_setting("wechat_token", token)

    if req.website_url is not None:
        if cs.is_website_url_from_env():
            raise HTTPException(status_code=400, detail="兑换网站地址由环境变量托管，禁止在网页后台修改")
        url = req.website_url.strip()
        if url and (len(url) > 256 or not (url.startswith("http://") or url.startswith("https://"))):
            raise HTTPException(status_code=400, detail="兑换网站地址必须以 http:// 或 https:// 开头且不超过 256 字")
        cs.set_setting("website_url", url)
        if url:
            set_custom_variable("site", url, "兑换网站地址")

    if req.group_id is not None:
        if cs.is_group_id_from_env():
            raise HTTPException(status_code=400, detail="微信群入口微信号由环境变量托管，禁止在网页后台修改")
        gid = req.group_id.strip()
        if len(gid) > 64:
            raise HTTPException(status_code=400, detail="微信群微信号长度不能超过 64 字")
        cs.set_setting("group_id", gid)
        if gid:
            set_custom_variable("group", gid, "微信群/客服入口微信号")

    if req.new_admin_password is not None and req.new_admin_password.strip():
        pwd = req.new_admin_password.strip()
        if len(pwd) < 8:
            raise HTTPException(status_code=400, detail="新管理员密码长度至少为 8 位")
        cs.set_admin_password(pwd)

    return {"status": "success", "message": "系统配置更新成功"}
