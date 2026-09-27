"""微信公众号通道适配器：处理微信 XML 报文与构建，委托领域服务完成业务流转。"""

import time
from typing import Optional

import core.services.code_service as code_svc
import core.services.dispatch_service as dispatch_svc
import core.services.message_service as message_svc
import core.services.user_service as user_svc


def build_reply_xml(from_user: str, to_user: str, reply_content: str) -> str:
    """构建安全转义的微信被动回复文本 XML 报文。"""
    safe = (reply_content or "").replace("]]>", "]]]]><![CDATA[>")
    return f"""<xml>
<ToUserName><![CDATA[{from_user}]]></ToUserName>
<FromUserName><![CDATA[{to_user}]]></FromUserName>
<CreateTime>{int(time.time())}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[{safe}]]></Content>
</xml>"""


# ----------------- 向后兼容委托函数 -----------------


def save_message(openid: str, msg_type: str, content: str, reply_content: str = ""):
    message_svc.save_message(openid, msg_type, content, reply_content)


def update_user_event(openid: str, event: str):
    user_svc.record_user_event(openid, event)


def decide_reply(msg_type: str, event: str, content: str, from_user: str) -> Optional[str]:
    return dispatch_svc.dispatch_reply(msg_type, event, content, from_user)


def assign_recipe_codes(openid: str, rule_id: int = 0, recipe_raw: str = ""):
    return code_svc.assign_recipe_codes(openid, rule_id, recipe_raw)


def assign_code(openid: str):
    return code_svc.assign_code(openid)
