from typing import Dict, List, Optional, Tuple

import core.services.code_service as code_svc
from core.security import escape_like
from db.database import db


def record_user_event(openid: str, event: str):
    """更新已记录用户的关注状态 (subscribe / unsubscribe)。"""
    if not openid or not event:
        return
    clean_event = event.strip().lower()
    try:
        with db() as conn:
            conn.execute("UPDATE users SET last_event = ? WHERE openid = ?", (clean_event, openid))
            conn.commit()
    except Exception:
        pass


def ensure_user_exists(openid: str, first_code: str = ""):
    """确保用户记录存在。若不存在则插入基础档案。"""
    if not openid:
        return
    try:
        with db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE openid = ?", (openid,))
            if not cursor.fetchone():
                cursor.execute(
                    "INSERT INTO users (openid, code, last_event) VALUES (?, ?, 'subscribe')",
                    (openid, first_code or ""),
                )
                conn.commit()
    except Exception:
        pass


def list_users(
    q: str = "",
    status: str = "",
    limit: int = 100,
    offset: int = 0,
) -> Tuple[int, List[dict]]:
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
                    "pool_key": row["pool_key"] or "default",
                })

            for u in users:
                c_list = user_claims_map.get(u["openid"], [])
                if not c_list and u.get("code"):
                    c_list = [{
                        "code": u["code"],
                        "pool_id": 1,
                        "pool_name": "默认池",
                        "pool_key": "default",
                    }]
                u["claims"] = c_list
                u["codes"] = [item["code"] for item in c_list]
                u["total_codes"] = len(c_list)
        return total, users


def reset_user(openid: str) -> Tuple[bool, List[str]]:
    """收回指定用户的激活码。单向调用 code_service.release_codes 释放卡密。
    返回 (ok, list_of_codes)。
    """
    clean_openid = (openid or "").strip()
    if not clean_openid:
        return False, []

    with db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT code FROM user_code_claims WHERE openid = ?", (clean_openid,))
        claim_rows = cursor.fetchall()
        codes = [r["code"] for r in claim_rows]

        # 兼容老数据（claims 暂未镜像时回退查 users）
        if not codes:
            cursor.execute("SELECT code FROM users WHERE openid = ?", (clean_openid,))
            u_row = cursor.fetchone()
            if u_row and u_row["code"]:
                codes = [u_row["code"]]

        if not codes:
            return False, []

        # 单向委托 code_service 释放激活码
        code_svc.release_codes(codes)

        # 本地事务清理关联记录
        cursor.execute("DELETE FROM user_code_claims WHERE openid = ?", (clean_openid,))
        cursor.execute("DELETE FROM users WHERE openid = ?", (clean_openid,))
        conn.commit()
        return True, codes


def reset_users_batch(openids: List[str]) -> Tuple[List[str], List[str]]:
    """批量重置用户。返回 (reset_list, not_found_list)。"""
    reset, not_found = [], []
    for oid in dict.fromkeys(openids or []):
        ok, _ = reset_user(oid)
        if ok:
            reset.append(oid)
        else:
            not_found.append(oid)
    return reset, not_found
