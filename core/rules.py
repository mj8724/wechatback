"""关键词回复规则引擎：规则按 priority 首个命中；支持 exact/contains/regex 匹配与多状态分支文案。"""

import json
import re
import time
from datetime import datetime
from typing import Dict, List, Optional

import config
import core.config_store as cs
from db.database import db


# ----------------- 自定义变量管理 -----------------


def list_custom_variables() -> List[dict]:
    with db() as conn:
        rows = conn.execute(
            "SELECT id, key, value, description, created_at FROM custom_variables ORDER BY id ASC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_custom_variables_map() -> Dict[str, str]:
    try:
        with db() as conn:
            rows = conn.execute("SELECT key, value FROM custom_variables").fetchall()
            return {r["key"]: r["value"] for r in rows}
    except Exception:
        return {}


def get_custom_variable(key: str, default: str = "") -> str:
    with db() as conn:
        row = conn.execute("SELECT value FROM custom_variables WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default


def set_custom_variable(key: str, value: str, description: str = "") -> int:
    clean_key = (key or "").strip().lower()
    clean_val = value or ""
    clean_desc = (description or "").strip()
    with db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM custom_variables WHERE key = ?", (clean_key,))
        row = cursor.fetchone()
        if row:
            cursor.execute(
                "UPDATE custom_variables SET value = ?, description = ? WHERE id = ?",
                (clean_val, clean_desc, row["id"]),
            )
            var_id = row["id"]
        else:
            cursor.execute(
                "INSERT INTO custom_variables (key, value, description) VALUES (?, ?, ?)",
                (clean_key, clean_val, clean_desc),
            )
            var_id = cursor.lastrowid
        conn.commit()
        return int(var_id or 0)


def delete_custom_variable(var_id: int) -> bool:
    with db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM custom_variables WHERE id = ?", (var_id,))
        conn.commit()
        return cursor.rowcount > 0


# ----------------- 规则加载与管理 -----------------


def load_rules() -> List[dict]:
    with db() as conn:
        rows = conn.execute(
            "SELECT id, keyword, mode, action, content, priority, enabled, recipe, "
            "status_replies, start_time, end_time "
            "FROM keyword_rules WHERE enabled = 1 ORDER BY priority ASC, id ASC"
        ).fetchall()
        return [dict(r) for r in rows]


def list_all_rules() -> List[dict]:
    with db() as conn:
        rows = conn.execute(
            "SELECT id, keyword, mode, action, content, priority, enabled, recipe, "
            "status_replies, start_time, end_time, created_at "
            "FROM keyword_rules ORDER BY priority ASC, id ASC"
        ).fetchall()
        return [dict(r) for r in rows]


from core.config_store import get_setting, set_setting


def get_pool_names_map() -> Dict[str, str]:
    """返回卡池 key -> name 映射字典。"""
    try:
        with db() as conn:
            rows = conn.execute("SELECT id, name, key FROM code_pools").fetchall()
            return {r["key"]: r["name"] for r in rows}
    except Exception:
        return {}


def get_stock_summary() -> str:
    """返回各池未领库存概览字符串，如 '默认卡券池: 88, GPT: 12'。"""
    try:
        with db() as conn:
            rows = conn.execute("""
                SELECT p.name,
                       SUM(CASE WHEN c.status = 'unused' THEN 1 ELSE 0 END) as unused
                FROM code_pools p
                LEFT JOIN codes c ON p.id = c.pool_id
                GROUP BY p.id
                ORDER BY p.id ASC
            """).fetchall()
            parts = [f"{r['name']}: {r['unused'] or 0}" for r in rows]
            return ", ".join(parts)
    except Exception:
        return ""


# ----------------- 规则匹配与时效状态 -----------------


def match_rule_keyword(rule: dict, content: str) -> bool:
    """检查输入文本是否匹配规则关键词。支持 contains / exact / regex 模式。"""
    text = (content or "").strip()
    kw = (rule.get("keyword") or "").strip()
    if not kw:
        return False
    mode = rule.get("mode", "contains")

    if mode == "exact":
        return text.lower() == kw.lower()
    elif mode == "regex":
        try:
            return bool(re.search(kw, text, re.IGNORECASE))
        except re.error:
            return False
    else:  # contains
        return kw.lower() in text.lower()


def check_rule_time_window(rule: dict) -> Optional[str]:
    """检查规则是否处于允许的活动时间窗口。
    返回:
      'not_started': 活动尚未开始
      'expired': 活动已经结束
      None: 在时间窗口内（合法）
    """
    now = datetime.now()
    start_str = (rule.get("start_time") or "").strip()
    end_str = (rule.get("end_time") or "").strip()

    if start_str:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                st = datetime.strptime(start_str, fmt)
                if now < st:
                    return "not_started"
                break
            except ValueError:
                pass

    if end_str:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                et = datetime.strptime(end_str, fmt)
                if now > et:
                    return "expired"
                break
            except ValueError:
                pass

    return None


def get_rule_status_reply(rule: dict, status: str) -> str:
    """提取规则中指定状态分支的回复文案。
    status ∈ 'new', 'repeat', 'empty', 'not_started', 'expired'
    """
    raw_replies = rule.get("status_replies") or ""
    replies_dict = {}
    if isinstance(raw_replies, dict):
        replies_dict = raw_replies
    elif isinstance(raw_replies, str) and raw_replies.strip():
        try:
            replies_dict = json.loads(raw_replies)
        except Exception:
            replies_dict = {}

    val = (replies_dict.get(status) or "").strip()
    if val:
        return val

    # 兜底默认值
    content = (rule.get("content") or "").strip()
    if status == "new":
        return content or "🎉 您的专属激活码为：\n\n【{code}】\n\n👉 兑换地址：{site}\n\n每个用户限领一次，请前往上方兑换地址完成充值兑换！"
    elif status == "repeat":
        return content or "您之前已成功领取过专属激活码：\n\n【{code}】\n\n👉 兑换地址：{site}\n每个用户限领一次，已领取的激活码可随时在上方平台完成兑换！"
    elif status == "empty":
        return get_setting("empty_reply") or "抱歉，当前激活码已被领完，请稍后再试或联系管理员！\n平台地址：{site}"
    elif status == "not_started":
        return "抱歉，本期激活码领取活动尚未开始，敬请期待！"
    elif status == "expired":
        return "抱歉，本期激活码领取活动已经结束，感谢您的关注！"
    return content


# ----------------- 富占位符渲染引擎 -----------------


def render(
    template: str,
    code: str = "",
    codes_map: Optional[Dict[str, List[str]]] = None,
    openid: str = "",
) -> str:
    """全功能富占位符渲染引擎。
    支持：
      {code}: 本规则发出的激活码（若组合发码则为首个码）
      {code.KEY}: 组合发码中指定品类下的激活码（多张以逗号分隔）
      {codes}: 结构化多品类清单
      {openid}: 粉丝 OpenID
      {date}: 日期 YYYY-MM-DD
      {time}: 时间 HH:MM:SS
      {stock}: 各池实时余量概览
      {site}: 兑换网站 URL（从全局自定义变量或配置获取）
      {group}: 微信群微信号（从全局自定义变量或配置获取）
      {任意自定义变量}: 匹配 custom_variables 表中的 key
    """
    text = template or ""
    first_code = code

    # 若未显式传 code 但传了 codes_map，取当前规则发出的首张码作为 {code}
    if not first_code and codes_map:
        for c_list in codes_map.values():
            if c_list:
                first_code = c_list[0]
                break

    # 1. 基础单码
    text = text.replace("{code}", first_code or "")

    # 2. 结构化多品类清单 {codes}
    if "{codes}" in text:
        if codes_map:
            name_map = get_pool_names_map()
            lines = []
            for k, c_list in codes_map.items():
                if not c_list:
                    continue
                p_name = name_map.get(k, k)
                lines.append(f"【{p_name}】：{', '.join(c_list)}")
            text = text.replace("{codes}", "\n".join(lines))
        else:
            text = text.replace("{codes}", first_code or "")

    # 3. 指定品类码 {code.KEY} (大小写不敏感匹配)
    if "{code." in text:
        lower_map = {k.lower(): v for k, v in (codes_map or {}).items()}
        for m in re.finditer(r"\{code\.([a-zA-Z0-9_]+)\}", text):
            match_str = m.group(0)
            target_key = m.group(1).lower()
            val_list = lower_map.get(target_key, [])
            replacement = ", ".join(val_list) if val_list else ""
            text = text.replace(match_str, replacement)

    # 4. 粉丝标识与时间占位符
    text = text.replace("{openid}", openid or "")
    text = text.replace("{date}", time.strftime("%Y-%m-%d"))
    text = text.replace("{time}", time.strftime("%H:%M:%S"))

    # 5. 实时库存概览
    if "{stock}" in text:
        text = text.replace("{stock}", get_stock_summary())

    # 6. 全局自定义变量（含 site, group 及用户新增的任意变量）
    custom_vars = get_custom_variables_map()
    if "site" not in custom_vars:
        custom_vars["site"] = cs.get_website_url()
    if "group" not in custom_vars:
        custom_vars["group"] = cs.get_group_id()

    for k, v in custom_vars.items():
        placeholder = "{" + k + "}"
        if placeholder in text:
            text = text.replace(placeholder, str(v))

    return text
