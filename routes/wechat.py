import hashlib
import hmac
import logging
import time
import xml.etree.ElementTree as ET

from fastapi import APIRouter, Request, Response

import config
import core.config_store as cs
import core.services.dispatch_service as dispatch_svc
import core.services.message_service as message_svc
import core.services.user_service as user_svc
from core.security import check_openid_throttle, check_wechat_throttle, get_client_ip
from core.wechat import build_reply_xml

logger = logging.getLogger("wechat")

router = APIRouter()

SUCCESS = Response(content="success", media_type="text/plain")


def verify_signature(signature: str, timestamp: str, nonce: str) -> bool:
    if not signature or not timestamp or not nonce:
        return False
    current_token = cs.get_wechat_token()
    if not current_token:
        logger.warning("WeChat Token not configured in env or database")
        return False
    try:
        ts = int(timestamp)
    except ValueError:
        return False
    if abs(time.time() - ts) > config.WECHAT_TS_WINDOW:
        return False
    items = [current_token, timestamp, nonce]
    items.sort()
    sha1 = hashlib.sha1("".join(items).encode("utf-8")).hexdigest()
    return hmac.compare_digest(sha1, signature)


@router.get("/MP_verify_{token}.txt")
def mp_verify_wildcard(token: str):
    return Response(content=token, media_type="text/plain")


@router.get("/healthz", include_in_schema=False)
def healthz():
    return {"status": "ok"}


@router.get("/wechat")
def verify_wechat(signature: str = "", timestamp: str = "", nonce: str = "", echostr: str = ""):
    if not cs.is_wechat_configured():
        return Response(content="WeChat Token Not Configured. Please configure in Admin Dashboard.", status_code=403)
    if verify_signature(signature, timestamp, nonce):
        return Response(content=echostr, media_type="text/plain")
    return Response(content="Invalid Signature", status_code=403)


@router.post("/wechat")
async def handle_wechat_msg(
    request: Request, signature: str = "", timestamp: str = "", nonce: str = ""
):
    # 先验签：失败只回 success（避免微信重试），不执行业务
    if not verify_signature(signature, timestamp, nonce):
        logger.info("wechat signature reject")
        return SUCCESS
    if not check_wechat_throttle(get_client_ip(request)):
        logger.info("wechat ip throttled")
        return SUCCESS

    body = await request.body()
    if len(body) > config.WECHAT_MAX_BODY:
        return SUCCESS
    lowered = body.lower()
    if b"<!doctype" in lowered or b"<!entity" in lowered:
        return SUCCESS
    try:
        root = ET.fromstring(body)
    except Exception:
        return SUCCESS

    msg_type = root.findtext("MsgType", "")
    from_user = root.findtext("FromUserName", "")  # 用户 OpenID
    to_user = root.findtext("ToUserName", "")      # 公众号原始ID
    event = root.findtext("Event", "").lower()
    content = root.findtext("Content", "") or ""
    if not check_openid_throttle(from_user):
        logger.info("wechat openid throttled")
        return SUCCESS

    # 事件关注/取关状态跟踪
    if msg_type == "event":
        if event in ["subscribe", "scan"]:
            user_svc.record_user_event(from_user, "subscribe")
        elif event == "unsubscribe":
            user_svc.record_user_event(from_user, "unsubscribe")

    reply_content = dispatch_svc.dispatch_reply(msg_type, event, content, from_user)

    # 消息与回复闭环持久化记录
    msg_body = content or (f"[{event}]" if msg_type == "event" else content)
    message_svc.save_message(from_user, msg_type, msg_body, reply_content or "")

    if reply_content is not None:
        return Response(content=build_reply_xml(from_user, to_user, reply_content), media_type="application/xml; charset=utf-8")

    return SUCCESS
