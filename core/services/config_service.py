from typing import Any, Dict, Optional, Tuple

from fastapi import HTTPException

import config
import core.config_store as cs
from core.auth import issue_token
from core.rules import set_custom_variable
from core.security import record_login_failure, record_login_success


def setup_initial(
    admin_password: str,
    wechat_token: str = "",
    website_url: str = "",
    group_id: str = "",
    ip: str = "",
) -> Dict[str, Any]:
    if cs.is_setup_done():
        if ip:
            record_login_failure(ip)
        raise HTTPException(status_code=403, detail="系统已完成初始化，禁止重复设置")

    pwd = (admin_password or "").strip()
    if len(pwd) < 8:
        raise HTTPException(status_code=400, detail="管理员密码长度至少为 8 位")

    cs.set_admin_password(pwd)

    if wechat_token:
        token = wechat_token.strip()
        if len(token) > 128:
            raise HTTPException(status_code=400, detail="微信 Token 长度不能超过 128 位")
        if not cs.is_wechat_token_from_env():
            cs.set_setting("wechat_token", token)

    if website_url:
        url = website_url.strip()
        if len(url) > 256 or not (url.startswith("http://") or url.startswith("https://")):
            raise HTTPException(status_code=400, detail="兑换网站地址必须以 http:// 或 https:// 开头且不超过 256 字")
        if not cs.is_website_url_from_env():
            cs.set_setting("website_url", url)
            set_custom_variable("site", url, "兑换网站地址")

    if group_id:
        gid = group_id.strip()
        if len(gid) > 64:
            raise HTTPException(status_code=400, detail="群入口微信号长度不能超过 64 字")
        if not cs.is_group_id_from_env():
            cs.set_setting("group_id", gid)
            set_custom_variable("group", gid, "微信群/客服入口微信号")

    if ip:
        record_login_success(ip)
    token, expires_at = issue_token()
    return {"status": "success", "token": token, "expires_at": expires_at, "message": "初始化设置成功"}


def update_system_config(
    wechat_token: Optional[str] = None,
    website_url: Optional[str] = None,
    group_id: Optional[str] = None,
    new_admin_password: Optional[str] = None,
):
    if wechat_token is not None:
        if cs.is_wechat_token_from_env():
            raise HTTPException(status_code=400, detail="微信 Token 由环境变量托管，禁止在网页后台修改")
        token = wechat_token.strip()
        if len(token) > 128:
            raise HTTPException(status_code=400, detail="微信 Token 长度不能超过 128 位")
        cs.set_setting("wechat_token", token)

    if website_url is not None:
        if cs.is_website_url_from_env():
            raise HTTPException(status_code=400, detail="兑换网站地址由环境变量托管，禁止在网页后台修改")
        url = website_url.strip()
        if url and (len(url) > 256 or not (url.startswith("http://") or url.startswith("https://"))):
            raise HTTPException(status_code=400, detail="兑换网站地址必须以 http:// 或 https:// 开头且不超过 256 字")
        cs.set_setting("website_url", url)
        if url:
            set_custom_variable("site", url, "兑换网站地址")

    if group_id is not None:
        if cs.is_group_id_from_env():
            raise HTTPException(status_code=400, detail="微信群入口微信号由环境变量托管，禁止在网页后台修改")
        gid = group_id.strip()
        if len(gid) > 64:
            raise HTTPException(status_code=400, detail="微信群微信号长度不能超过 64 字")
        cs.set_setting("group_id", gid)
        if gid:
            set_custom_variable("group", gid, "微信群/客服入口微信号")

    if new_admin_password is not None and new_admin_password.strip():
        pwd = new_admin_password.strip()
        if len(pwd) < 8:
            raise HTTPException(status_code=400, detail="新管理员密码长度至少为 8 位")
        cs.set_admin_password(pwd)
