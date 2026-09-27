import json
import re
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException

from core.rules import list_all_rules
from core.schemas import RuleImportItem, RuleRequest
from db.database import db


def _serialize_status_replies(val: Any) -> str:
    if val is None:
        return ""
    if isinstance(val, str):
        return val
    try:
        return json.dumps(val, ensure_ascii=False)
    except Exception:
        return ""


def check_rule_payload(req: RuleRequest) -> str:
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


def list_rules() -> List[dict]:
    return list_all_rules()


def create_rule(req: RuleRequest) -> int:
    kw = check_rule_payload(req)
    sr_str = _serialize_status_replies(req.status_replies)
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO keyword_rules (keyword, mode, action, content, priority, enabled, recipe, status_replies, start_time, end_time) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (kw, req.mode, req.action, req.content or "", int(req.priority), 1 if req.enabled else 0, req.recipe or "", sr_str, req.start_time or "", req.end_time or ""),
        )
        conn.commit()
        return cur.lastrowid or 0


def update_rule(rule_id: int, req: RuleRequest) -> bool:
    kw = check_rule_payload(req)
    sr_str = _serialize_status_replies(req.status_replies)
    with db() as conn:
        cur = conn.execute(
            "UPDATE keyword_rules SET keyword = ?, mode = ?, action = ?, content = ?, "
            "priority = ?, enabled = ?, recipe = ?, status_replies = ?, start_time = ?, end_time = ? WHERE id = ?",
            (kw, req.mode, req.action, req.content or "", int(req.priority), 1 if req.enabled else 0, req.recipe or "", sr_str, req.start_time or "", req.end_time or "", rule_id),
        )
        conn.commit()
        return cur.rowcount > 0


def delete_rule(rule_id: int) -> bool:
    with db() as conn:
        cur = conn.execute("DELETE FROM keyword_rules WHERE id = ?", (rule_id,))
        conn.commit()
        return cur.rowcount > 0


def batch_delete_rules(ids: List[int]) -> int:
    valid_ids = [int(i) for i in (ids or []) if i > 0]
    if not valid_ids:
        return 0
    with db() as conn:
        placeholders = ",".join("?" for _ in valid_ids)
        cur = conn.execute(f"DELETE FROM keyword_rules WHERE id IN ({placeholders})", valid_ids)
        conn.commit()
        return cur.rowcount


def batch_toggle_rules(ids: List[int], enabled: bool) -> int:
    valid_ids = [int(i) for i in (ids or []) if i > 0]
    if not valid_ids:
        return 0
    val = 1 if enabled else 0
    with db() as conn:
        placeholders = ",".join("?" for _ in valid_ids)
        cur = conn.execute(f"UPDATE keyword_rules SET enabled = ? WHERE id IN ({placeholders})", [val, *valid_ids])
        conn.commit()
        return cur.rowcount


def batch_import_rules(rules: List[RuleImportItem], mode: str = "skip") -> Dict[str, int]:
    added, updated, skipped = 0, 0, 0

    with db() as conn:
        cursor = conn.cursor()
        for item in rules:
            kw = (item.keyword or "").strip()
            if not kw or len(kw) > 128:
                continue
            m = item.mode if item.mode in ("contains", "exact", "regex") else "contains"
            action = item.action if item.action in ("none", "code", "event_subscribe", "event_fallback") else "none"
            content = (item.content or "")[:2000]
            priority = max(0, min(int(item.priority or 100), 10000))
            enabled = 1 if item.enabled else 0
            recipe = item.recipe or ""
            sr_str = _serialize_status_replies(item.status_replies)
            st_str = item.start_time or ""
            et_str = item.end_time or ""

            cursor.execute("SELECT id FROM keyword_rules WHERE keyword = ? AND mode = ?", (kw, m))
            existing = cursor.fetchone()
            if existing:
                if mode == "overwrite":
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
                """, (kw, m, action, content, priority, enabled, recipe, sr_str, st_str, et_str))
                added += 1
        conn.commit()

    return {"added": added, "updated": updated, "skipped": skipped, "total": added + updated + skipped}
