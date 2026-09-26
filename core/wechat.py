import json
import sqlite3
import time
from typing import Any, Dict, List, Optional, Tuple

import config
from core.rules import check_rule_time_window, get_rule_status_reply, get_setting, load_rules, match_rule_keyword, render
from db.database import db

MAX_ASSIGN_RETRIES = 5


def save_message(openid: str, msg_type: str, content: str, reply_content: str = ""):
    try:
        with db() as conn:
            conn.execute(
                "INSERT INTO messages (openid, msg_type, content, reply_content) VALUES (?, ?, ?, ?)",
                (openid, msg_type, content, reply_content or "")
            )
            conn.commit()
    except Exception:
        pass


def update_user_event(openid: str, event: str):
    """更新已记录用户的关注状态 (subscribe / unsubscribe)。"""
    if not openid or not event:
        return
    try:
        with db() as conn:
            conn.execute("UPDATE users SET last_event = ? WHERE openid = ?", (event.strip().lower(), openid))
            conn.commit()
    except Exception:
        pass


def parse_recipe(conn, recipe_raw: str) -> List[Dict[str, Any]]:
    """解析发码配方。为空或非法时回退到默认品类池 1 张码。"""
    cursor = conn.cursor()
    cursor.execute("SELECT id, key FROM code_pools ORDER BY id ASC")
    pool_rows = cursor.fetchall()
    id_to_key = {r["id"]: r["key"] for r in pool_rows}
    key_to_id = {r["key"]: r["id"] for r in pool_rows}

    recipe_items = []
    if recipe_raw and isinstance(recipe_raw, str):
        try:
            data = json.loads(recipe_raw.strip())
            if isinstance(data, list):
                for item in data:
                    if not isinstance(item, dict):
                        continue
                    count = int(item.get("count", 1))
                    if count <= 0:
                        continue
                    pool_id = item.get("pool_id")
                    key = item.get("key")
                    if pool_id is not None and int(pool_id) in id_to_key:
                        p_id = int(pool_id)
                        p_key = id_to_key[p_id]
                    elif key and str(key).lower() in key_to_id:
                        p_key = str(key).lower()
                        p_id = key_to_id[p_key]
                    else:
                        continue
                    recipe_items.append({"pool_id": p_id, "key": p_key, "count": count})
        except Exception:
            pass

    if not recipe_items:
        default_id = pool_rows[0]["id"] if pool_rows else 1
        default_key = pool_rows[0]["key"] if pool_rows else "default"
        recipe_items = [{"pool_id": default_id, "key": default_key, "count": 1}]

    return recipe_items


def _claim_recipe_codes(conn, openid: str, rule_id: int, recipe_raw: str) -> Tuple[Optional[Dict[str, Any]], str]:
    """单次配方发码尝试。
    返回 (data, kind)，其中 kind ∈ 'existing' | 'new' | 'empty' | 'retry' | 'error'。
    """
    cursor = conn.cursor()

    # 1. 检查粉丝该 rule_id 是否已领取过（一人一套码查重）
    cursor.execute("""
        SELECT ucc.code, ucc.pool_id, p.key as pool_key
        FROM user_code_claims ucc
        LEFT JOIN code_pools p ON ucc.pool_id = p.id
        WHERE ucc.openid = ? AND ucc.rule_id = ?
        ORDER BY ucc.id ASC
    """, (openid, rule_id))
    claims = cursor.fetchall()

    # 兼容历史数据（若 rule_id=0 且 claims 为空，检查 users 表）
    if not claims and rule_id == 0:
        cursor.execute("SELECT code FROM users WHERE openid = ?", (openid,))
        u = cursor.fetchone()
        if u and u["code"]:
            claims = [{"code": u["code"], "pool_id": 1, "pool_key": "default"}]

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


def _claim_code(conn, openid: str):
    """向后兼容单次发码尝试。"""
    data, kind = _claim_recipe_codes(conn, openid, rule_id=0, recipe_raw="")
    code_val = data["first_code"] if data else None
    return code_val, kind


def decide_reply(msg_type: str, event: str, content: str, from_user: str) -> Optional[str]:
    all_active_rules = load_rules()

    # 1. 关注/扫码事件
    if msg_type == "event" and event in ["subscribe", "scan"]:
        for rule in all_active_rules:
            if rule.get("action") == "event_subscribe":
                return render(rule.get("content") or "", openid=from_user)
        return None

    if msg_type != "text":
        return None

    # 2. 文本关键词规则匹配
    for rule in all_active_rules:
        action = rule.get("action", "")
        if action.startswith("event_"):
            continue

        if not match_rule_keyword(rule, content):
            continue

        if action == "code":
            time_status = check_rule_time_window(rule)
            if time_status in ("not_started", "expired"):
                tpl = get_rule_status_reply(rule, time_status)
                return render(tpl, openid=from_user)

            return render_code_reply_with_rule(rule, from_user)

        return render(rule.get("content") or "", openid=from_user)

    # 3. 兜底未识别回复（优先查启用的 event_fallback 规则）
    for rule in all_active_rules:
        if rule.get("action") == "event_fallback":
            return render(rule.get("content") or "", openid=from_user)

    return None


def render_code_reply_with_rule(rule: dict, openid: str) -> str:
    """根据规则定义与发码状态（首发/已领/缺货）分支渲染回复。"""
    rule_id = rule.get("id", 0)
    recipe_raw = rule.get("recipe", "")
    data, kind = assign_recipe_codes(openid, rule_id, recipe_raw)

    if kind in ("retry", "error"):
        return "系统繁忙，请稍后再试！"

    status_key = "repeat" if kind == "existing" else kind
    tpl = get_rule_status_reply(rule, status_key)

    codes_map = data.get("codes_map") if data else {}
    first_code = data.get("first_code", "") if data else ""
    return render(tpl, code=first_code, codes_map=codes_map, openid=openid)


def render_code_reply(template: str, openid: str, rule_id: int = 0, recipe_raw: str = "") -> str:
    """向后兼容发码渲染函数。"""
    rule = {"id": rule_id, "recipe": recipe_raw, "content": template}
    return render_code_reply_with_rule(rule, openid)


def assign_recipe_codes(openid: str, rule_id: int = 0, recipe_raw: str = ""):
    """组合发码并返回 (data, kind)。"""
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


def build_reply_xml(from_user: str, to_user: str, reply_content: str) -> str:
    safe = (reply_content or "").replace("]]>", "]]]]><![CDATA[>")
    return f"""<xml>
<ToUserName><![CDATA[{from_user}]]></ToUserName>
<FromUserName><![CDATA[{to_user}]]></FromUserName>
<CreateTime>{int(time.time())}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[{safe}]]></Content>
</xml>"""
