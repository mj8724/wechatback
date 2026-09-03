import hashlib
import xml.etree.ElementTree as ET

from fastapi import APIRouter, Request, Response

import config
from core.wechat import build_reply_xml, decide_reply, save_message

router = APIRouter()


@router.get("/MP_verify_{token}.txt")
def mp_verify_wildcard(token: str):
    return Response(content=token, media_type="text/plain")


@router.get("/wechat")
def verify_wechat(signature: str = "", timestamp: str = "", nonce: str = "", echostr: str = ""):
    items = [config.WECHAT_TOKEN, timestamp, nonce]
    items.sort()
    sha1 = hashlib.sha1("".join(items).encode("utf-8")).hexdigest()
    if sha1 == signature:
        return Response(content=echostr, media_type="text/plain")
    return Response(content="Invalid Signature", status_code=403)


@router.post("/wechat")
async def handle_wechat_msg(request: Request):
    body = await request.body()
    try:
        root = ET.fromstring(body)
    except Exception:
        return Response(content="success", media_type="text/plain")

    msg_type = root.findtext("MsgType", "")
    from_user = root.findtext("FromUserName", "")  # 用户 OpenID
    to_user = root.findtext("ToUserName", "")      # 公众号原始ID
    event = root.findtext("Event", "").lower()
    content = root.findtext("Content", "") or ""

    # 所有消息一律先持久化记录
    save_message(from_user, msg_type, content or f"[{event}]" if msg_type == "event" else content)

    reply_content = decide_reply(msg_type, event, content, from_user)

    if reply_content is not None:
        return Response(content=build_reply_xml(from_user, to_user, reply_content), media_type="application/xml")

    return Response(content="success", media_type="text/plain")
