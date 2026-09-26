"""关键词回复规则引擎：规则按 priority 首个命中；占位符 {code} {site} {group}。"""

import re
import time
from typing import Optional, Dict, List

import config
import core.config_store as cs
from db.database import db


def load_rules():
    with db() as conn:
        rows = conn.execute(
            "SELECT id, keyword, mode, action, content, priority, enabled, recipe "
            "FROM keyword_rules WHERE enabled = 1 ORDER BY priority ASC, id ASC"
        ).fetchall()
        return [dict(r) for r in rows]


def list_all_rules():
    with db() as conn:
        rows = conn.execute(
            "SELECT id, keyword, mode, action, content, priority, enabled, recipe, created_at "
            "FROM keyword_rules ORDER BY priority ASC, id ASC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_setting(key: str, default: str = "") -> str:
    with db() as conn:
        row = conn.execute("SELECT value FROM site_settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default


def set_setting(key: str, value: str):
    with db() as conn:
        conn.execute(
            "INSERT INTO site_settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        conn.commit()


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
      {site}: 兑换网站 URL
      {group}: 微信群微信号
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

    # 6. 站点与社群设置
    text = text.replace("{site}", cs.get_website_url())
    text = text.replace("{group}", cs.get_group_id())

    return text
