import json
import re
import sqlite3
import time
from typing import Any, Dict, List, Optional, Tuple

from core.security import escape_like
from db.database import db

MAX_ASSIGN_RETRIES = 5


def list_pools() -> List[dict]:
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
        return pools


def set_default_pool(pool_id: int) -> bool:
    with db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM code_pools WHERE id = ?", (pool_id,))
        if not cursor.fetchone():
            return False
        cursor.execute("UPDATE code_pools SET is_default = 0")
        cursor.execute("UPDATE code_pools SET is_default = 1 WHERE id = ?", (pool_id,))
        conn.commit()
        return True


def create_pool(name: str, key: str, description: str = "") -> Tuple[int, Optional[str]]:
    clean_name = (name or "").strip()
    clean_key = (key or "").strip().lower()
    clean_desc = (description or "").strip()

    if not clean_name or len(clean_name) > 64:
        return 0, "卡池名称不能为空且最多 64 字"
    if not re.match(r"^[a-z0-9_]{1,32}$", clean_key):
        return 0, "卡池标识 key 只能由 1~32 位小写字母、数字和下划线组成"

    with db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM code_pools WHERE key = ?", (clean_key,))
        if cursor.fetchone():
            return 0, f"卡池标识 key '{clean_key}' 已存在"
        cursor.execute(
            "INSERT INTO code_pools (name, key, description) VALUES (?, ?, ?)",
            (clean_name, clean_key, clean_desc),
        )
        conn.commit()
        return cursor.lastrowid or 0, None


def update_pool(pool_id: int, name: str, description: str = "") -> Tuple[bool, Optional[str]]:
    clean_name = (name or "").strip()
    clean_desc = (description or "").strip()
    if not clean_name or len(clean_name) > 64:
        return False, "卡池名称不能为空且最多 64 字"

    with db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE code_pools SET name = ?, description = ? WHERE id = ?",
            (clean_name, clean_desc, pool_id),
        )
        conn.commit()
        if cursor.rowcount == 0:
            return False, "卡池不存在"
        return True, None


def delete_pool(pool_id: int) -> Tuple[bool, Optional[str]]:
    if pool_id == 1:
        return False, "默认卡券池禁止删除"

    with db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM code_pools WHERE id = ?", (pool_id,))
        if not cursor.fetchone():
            return False, "卡池不存在"
        cursor.execute("SELECT COUNT(*) as n FROM codes WHERE pool_id = ?", (pool_id,))
        if cursor.fetchone()["n"] > 0:
            return False, "该卡池内尚有激活码，请先清空或删除激活码后再删除卡池"
        cursor.execute("DELETE FROM code_pools WHERE id = ?", (pool_id,))
        conn.commit()
        return True, None


def import_codes(
    codes: Optional[List[str]] = None,
    pool_id: Optional[int] = 1,
    multi_pool_codes: Optional[Dict[str, List[str]]] = None,
) -> Tuple[Dict[str, Any], Optional[str]]:
    added = 0
    duplicates = []
    by_pool = {}

    with db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, key FROM code_pools")
        pool_map = {r["key"]: r["id"] for r in cursor.fetchall()}
        id_to_key = {v: k for k, v in pool_map.items()}

        # 1. 多品类字典导入
        if multi_pool_codes:
            total_items = sum(len(c_list) for c_list in multi_pool_codes.values())
            if total_items > 2000:
                return {}, "单次最多导入 2000 个激活码"

            for p_key, code_list in multi_pool_codes.items():
                p_key_clean = (p_key or "").strip().lower()
                if p_key_clean not in pool_map:
                    return {}, f"未识别的卡池 key: '{p_key}'，请先创建对应卡池"
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
                        return {}, "单个激活码最多 128 字"
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
            return {
                "status": "success",
                "added": added,
                "duplicates": duplicates,
                "total": added + len(duplicates),
                "by_pool": by_pool,
            }, None

        # 2. 单池或默认池列表导入
        code_list = codes or []
        if len(code_list) > 2000:
            return {}, "单次最多导入 2000 个"
        target_pool_id = pool_id or 1
        if target_pool_id not in id_to_key:
            cursor.execute("SELECT id FROM code_pools WHERE id = ?", (target_pool_id,))
            if not cursor.fetchone():
                return {}, "目标卡池不存在"

        target_key = id_to_key.get(target_pool_id, str(target_pool_id))
        seen = set()
        for code in code_list:
            c = code.strip() if isinstance(code, str) else ""
            if not c or c in seen:
                if c:
                    duplicates.append(c)
                continue
            if len(c) > 128:
                return {}, "单个激活码最多 128 字"
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
        return {
            "status": "success",
            "added": added,
            "duplicates": duplicates,
            "total": added + len(duplicates),
            "by_pool": by_pool,
        }, None


def list_codes(
    q: str = "",
    status: str = "",
    pool_id: Optional[int] = None,
    limit: int = 100,
    offset: int = 0,
) -> Tuple[int, List[dict]]:
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
        return total, records


def delete_code(code: str) -> Tuple[bool, bool]:
    clean_code = (code or "").strip()
    if not clean_code:
        return False, False
    with db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM codes WHERE code = ?", (clean_code,))
        row = cursor.fetchone()
        if not row:
            return False, False
        was_assigned = row["status"] == "assigned"
        cursor.execute("DELETE FROM codes WHERE code = ?", (clean_code,))
        cursor.execute("DELETE FROM user_code_claims WHERE code = ?", (clean_code,))
        cursor.execute("DELETE FROM users WHERE code = ?", (clean_code,))
        conn.commit()
        return True, was_assigned


def delete_unused_codes(pool_id: Optional[int] = None) -> int:
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
        return n


def release_codes(codes: List[str]):
    """原子方法：仅释放激活码为 unused 状态，解绑 openid。"""
    if not codes:
        return
    with db() as conn:
        for c in codes:
            conn.execute(
                "UPDATE codes SET status = 'unused', assigned_openid = NULL, assigned_at = NULL WHERE code = ?",
                (c,),
            )
        conn.commit()


def reset_single_code(code: str) -> bool:
    clean_code = (code or "").strip()
    if not clean_code:
        return False
    with db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM codes WHERE code = ?", (clean_code,))
        if not cursor.fetchone():
            return False
        cursor.execute(
            "UPDATE codes SET status = 'unused', assigned_openid = NULL, assigned_at = NULL WHERE code = ?",
            (clean_code,),
        )
        cursor.execute("DELETE FROM user_code_claims WHERE code = ?", (clean_code,))
        cursor.execute("DELETE FROM users WHERE code = ?", (clean_code,))
        conn.commit()
        return True


def parse_recipe(conn, recipe_raw: str) -> List[Dict[str, Any]]:
    """解析规则中的配方字段。默认发放 1 张默认卡池卡密。"""
    cursor = conn.cursor()
    cursor.execute("SELECT id, key, is_default FROM code_pools")
    pools = cursor.fetchall()
    id_map = {r["id"]: r["key"] for r in pools}
    key_map = {r["key"]: r["id"] for r in pools}

    default_pool_id = 1
    for r in pools:
        if r["is_default"]:
            default_pool_id = r["id"]
            break

    if not recipe_raw or not recipe_raw.strip():
        return [{"pool_id": default_pool_id, "key": id_map.get(default_pool_id, "default"), "count": 1}]

    items = []
    text = recipe_raw.strip()
    if text.startswith("["):
        try:
            arr = json.loads(text)
            for item in arr:
                pid = item.get("pool_id")
                cnt = max(1, min(100, int(item.get("count", 1))))
                if pid in id_map:
                    items.append({"pool_id": pid, "key": id_map[pid], "count": cnt})
                elif item.get("key") in key_map:
                    target_pid = key_map[item["key"]]
                    items.append({"pool_id": target_pid, "key": item["key"], "count": cnt})
        except Exception:
            pass

    if not items:
        parts = text.split(",")
        for part in parts:
            if not part.strip():
                continue
            sub = part.strip().split(":")
            k = sub[0].strip().lower()
            cnt = int(sub[1].strip()) if len(sub) > 1 and sub[1].strip().isdigit() else 1
            cnt = max(1, min(100, cnt))
            if k in key_map:
                items.append({"pool_id": key_map[k], "key": k, "count": cnt})

    if not items:
        items = [{"pool_id": default_pool_id, "key": id_map.get(default_pool_id, "default"), "count": 1}]
    return items


def _claim_recipe_codes(conn, openid: str, rule_id: int = 0, recipe_raw: str = ""):
    """组合发码底层事务。
    返回 (data_dict, kind)，kind ∈ new/existing/empty/retry/error。
    """
    cursor = conn.cursor()

    # 1. 幂等性：同 openid 在此规则下是否已领过
    cursor.execute("""
        SELECT ucc.code, ucc.pool_id, p.key as pool_key
        FROM user_code_claims ucc
        LEFT JOIN code_pools p ON ucc.pool_id = p.id
        WHERE ucc.openid = ? AND ucc.rule_id = ?
        ORDER BY ucc.id ASC
    """, (openid, rule_id))
    claims = cursor.fetchall()
    if claims:
        codes_map = {}
        for r in claims:
            k = r["pool_key"] or "default"
            codes_map.setdefault(k, []).append(r["code"])
        return {"codes_map": codes_map, "first_code": claims[0]["code"]}, "existing"

    # 2. 解析配方
    recipe = parse_recipe(conn, recipe_raw)
    now_str = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())

    try:
        cursor.execute("BEGIN IMMEDIATE")

        # 检查各品类库存（All-or-Nothing 事务原子性）
        allocated = []
        for item in recipe:
            pid = item["pool_id"]
            cnt = item["count"]
            pkey = item["key"]
            cursor.execute(
                "SELECT id, code FROM codes WHERE pool_id = ? AND status = 'unused' ORDER BY id ASC LIMIT ?",
                (pid, cnt),
            )
            rows = cursor.fetchall()
            if len(rows) < cnt:
                conn.rollback()
                return None, "empty"
            for r in rows:
                allocated.append({"id": r["id"], "code": r["code"], "pool_id": pid, "key": pkey})

        # 锁定更新激活码并写入流水
        for alloc in allocated:
            cursor.execute(
                "UPDATE codes SET status = 'assigned', assigned_openid = ?, assigned_at = ? WHERE id = ? AND status = 'unused'",
                (openid, now_str, alloc["id"]),
            )
            if cursor.rowcount == 0:
                conn.rollback()
                return None, "retry"

            cursor.execute(
                "INSERT INTO user_code_claims (openid, rule_id, pool_id, code) VALUES (?, ?, ?, ?)",
                (openid, rule_id, alloc["pool_id"], alloc["code"]),
            )

        # 兼容老 users 表：若 openid 未记录，插入首码
        cursor.execute("SELECT id FROM users WHERE openid = ?", (openid,))
        if not cursor.fetchone() and allocated:
            cursor.execute(
                "INSERT INTO users (openid, code, last_event) VALUES (?, ?, 'subscribe')",
                (openid, allocated[0]["code"]),
            )

        conn.commit()

        codes_map = {}
        for alloc in allocated:
            codes_map.setdefault(alloc["key"], []).append(alloc["code"])
        first_code = allocated[0]["code"] if allocated else ""
        return {"codes_map": codes_map, "first_code": first_code}, "new"

    except sqlite3.IntegrityError:
        conn.rollback()
        cursor.execute("""
            SELECT ucc.code, ucc.pool_id, p.key as pool_key
            FROM user_code_claims ucc
            LEFT JOIN code_pools p ON ucc.pool_id = p.id
            WHERE ucc.openid = ? AND ucc.rule_id = ?
            ORDER BY ucc.id ASC
        """, (openid, rule_id))
        claims = cursor.fetchall()
        if claims:
            codes_map = {}
            for r in claims:
                k = r["pool_key"] or "default"
                codes_map.setdefault(k, []).append(r["code"])
            return {"codes_map": codes_map, "first_code": claims[0]["code"]}, "existing"
        return None, "retry"
    except Exception:
        conn.rollback()
        return None, "error"


def assign_recipe_codes(openid: str, rule_id: int = 0, recipe_raw: str = ""):
    """组合发码并返回 (data, kind)。包含外层连接级 MAX_ASSIGN_RETRIES 重试保障。"""
    if not openid:
        return None, "error"
    data, kind = None, "retry"
    for _ in range(MAX_ASSIGN_RETRIES):
        with db() as conn:
            data, kind = _claim_recipe_codes(conn, openid, rule_id, recipe_raw)
        if kind != "retry":
            break
    return data, kind


def assign_code(openid: str):
    """向后兼容单码发码接口。返回 (first_code, kind)。"""
    data, kind = assign_recipe_codes(openid, rule_id=0, recipe_raw="")
    first_code = data["first_code"] if data else None
    return first_code, kind
