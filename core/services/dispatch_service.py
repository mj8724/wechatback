from typing import Optional

import core.services.code_service as code_svc
from core.rules import (
    check_rule_time_window,
    get_rule_status_reply,
    load_rules,
    match_rule_keyword,
    render,
)


def dispatch_reply(
    msg_type: str,
    event: str,
    content: str,
    user_id: str,
) -> Optional[str]:
    """渠道无关的全局业务决策调度引擎。
    支持事件规则、关键词匹配（exact/contains/regex）、活动时限拦截与发码多状态独立分支。
    """
    all_active_rules = load_rules()

    # 1. 关注/扫码事件
    if msg_type == "event" and event in ["subscribe", "scan"]:
        for rule in all_active_rules:
            if rule.get("action") == "event_subscribe":
                return render(rule.get("content") or "", openid=user_id)
        return None

    if msg_type != "text":
        return None

    # 2. 文本关键词规则扫描
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
                return render(tpl, openid=user_id)

            return render_code_reply_with_rule(rule, user_id)

        return render(rule.get("content") or "", openid=user_id)

    # 3. 兜底未识别回复
    for rule in all_active_rules:
        if rule.get("action") == "event_fallback":
            return render(rule.get("content") or "", openid=user_id)

    return None


def render_code_reply_with_rule(rule: dict, user_id: str) -> str:
    """根据规则定义与发码状态（首发/已领/缺货）分支渲染回复。"""
    rule_id = rule.get("id", 0)
    recipe_raw = rule.get("recipe", "")
    data, kind = code_svc.assign_recipe_codes(user_id, rule_id, recipe_raw)

    if kind in ("retry", "error"):
        return "系统繁忙，请稍后再试！"

    status_key = "repeat" if kind == "existing" else kind
    tpl = get_rule_status_reply(rule, status_key)

    codes_map = data.get("codes_map") if data else {}
    first_code = data.get("first_code", "") if data else ""
    return render(tpl, code=first_code, codes_map=codes_map, openid=user_id)
