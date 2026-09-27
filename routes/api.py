from typing import Any, List, Optional

from fastapi import APIRouter, HTTPException, Request

import config
import core.config_store as cs
import core.services.code_service as code_svc
import core.services.config_service as config_svc
import core.services.message_service as message_svc
import core.services.rule_service as rule_svc
import core.services.stats_service as stats_svc
import core.services.user_service as user_svc
from core.auth import bearer_token, issue_token, require_admin, revoke_all_tokens, revoke_token
from core.rules import delete_custom_variable, list_custom_variables, set_custom_variable
from core.schemas import (
    CodeRequest,
    ConfigUpdateRequest,
    ImportRequest,
    LoginRequest,
    PoolCreateRequest,
    PoolUpdateRequest,
    RuleBatchDeleteRequest,
    RuleBatchImportRequest,
    RuleBatchToggleRequest,
    RuleRequest,
    SetupRequest,
    UserBatchResetRequest,
    UserResetRequest,
    VariableCreateRequest,
    VariableUpdateRequest,
)
from core.security import check_rate_limit, get_client_ip, is_valid_pwd, record_login_failure, record_login_success

router = APIRouter()


# ----------------- 系统初始化与认证 -----------------


@router.get("/api/setup/status")
def setup_status():
    """公开接口：获取系统初始化及微信 Token 配置状态，供前端路由守卫使用。"""
    return {
        "status": "success",
        "setup_done": cs.is_setup_done(),
        "wechat_configured": cs.is_wechat_configured(),
    }


@router.post("/api/setup")
def setup_initial(req: SetupRequest, request: Request):
    """公开接口：系统未初始化时进行首发配置，设置管理密码和可选的微信Token。"""
    ip = get_client_ip(request)
    check_rate_limit(ip)
    return config_svc.setup_initial(
        admin_password=req.admin_password,
        wechat_token=req.wechat_token,
        website_url=req.website_url,
        group_id=req.group_id,
        ip=ip,
    )


@router.post("/api/login")
def login(req: LoginRequest, request: Request):
    ip = get_client_ip(request)
    check_rate_limit(ip)
    if not is_valid_pwd(req.pwd):
        record_login_failure(ip)
        raise HTTPException(status_code=401, detail="密码错误")
    record_login_success(ip)
    token, expires_at = issue_token()
    return {"status": "success", "token": token, "expires_at": expires_at}


@router.post("/api/logout")
def logout(request: Request):
    token = bearer_token(request)
    if token:
        revoke_token(token)
    return {"status": "success"}


# ----------------- 仪表盘与统计 -----------------


@router.get("/api/stats")
def get_stats(request: Request):
    require_admin(request)
    return stats_svc.get_dashboard_stats()


# ----------------- 卡池管理 -----------------


@router.get("/api/pools")
def list_pools(request: Request):
    require_admin(request)
    return {"status": "success", "pools": code_svc.list_pools()}


@router.post("/api/pools/{pool_id}/set-default")
def set_default_pool(pool_id: int, request: Request):
    require_admin(request)
    ok = code_svc.set_default_pool(pool_id)
    if not ok:
        raise HTTPException(status_code=404, detail="卡池不存在")
    return {"status": "success", "message": "已成功设置为主卡池，{code} 占位符将绑定此卡池"}


@router.post("/api/pools")
def create_pool(req: PoolCreateRequest, request: Request):
    require_admin(request)
    pool_id, err = code_svc.create_pool(req.name, req.key, req.description)
    if err:
        raise HTTPException(status_code=400, detail=err)
    return {"status": "success", "id": pool_id}


@router.put("/api/pools/{pool_id}")
def update_pool(pool_id: int, req: PoolUpdateRequest, request: Request):
    require_admin(request)
    ok, err = code_svc.update_pool(pool_id, req.name, req.description)
    if err:
        status_code = 404 if err == "卡池不存在" else 400
        raise HTTPException(status_code=status_code, detail=err)
    return {"status": "success"}


@router.delete("/api/pools/{pool_id}")
def delete_pool(pool_id: int, request: Request):
    require_admin(request)
    ok, err = code_svc.delete_pool(pool_id)
    if err:
        status_code = 404 if err == "卡池不存在" else 400
        raise HTTPException(status_code=status_code, detail=err)
    return {"status": "success"}


# ----------------- 激活码导入与维护 -----------------


@router.post("/api/import")
def import_codes(req: ImportRequest, request: Request):
    require_admin(request)
    data, err = code_svc.import_codes(
        codes=req.codes,
        pool_id=req.pool_id,
        multi_pool_codes=req.multi_pool_codes,
    )
    if err:
        raise HTTPException(status_code=400, detail=err)
    return data


@router.get("/api/codes")
def list_codes(request: Request, q: str = "", status: str = "", pool_id: Optional[int] = None, limit: int = 100, offset: int = 0):
    require_admin(request)
    total, records = code_svc.list_codes(q=q, status=status, pool_id=pool_id, limit=limit, offset=offset)
    return {"status": "success", "total": total, "codes": records}


@router.post("/api/codes/reset")
def reset_code(req: CodeRequest, request: Request):
    require_admin(request)
    code = (req.code or "").strip()
    if not code:
        raise HTTPException(status_code=400, detail="激活码不能为空")
    ok = code_svc.reset_single_code(code)
    if not ok:
        raise HTTPException(status_code=404, detail="激活码不存在")
    return {"status": "success", "message": "已重置为未使用"}


@router.post("/api/codes/delete")
def delete_code(req: CodeRequest, request: Request):
    require_admin(request)
    code = (req.code or "").strip()
    if not code:
        raise HTTPException(status_code=400, detail="激活码不能为空")
    found, was_assigned = code_svc.delete_code(code)
    if not found:
        raise HTTPException(status_code=404, detail="激活码不存在")
    return {"status": "success", "message": "已删除" + ("（原领取人绑定已解除）" if was_assigned else "")}


@router.post("/api/codes/delete-unused")
def delete_unused_codes(request: Request, pool_id: Optional[int] = None):
    require_admin(request)
    n = code_svc.delete_unused_codes(pool_id)
    return {"status": "success", "deleted": n, "message": f"已清空 {n} 个未使用激活码"}


# ----------------- 粉丝与消息审计 -----------------


@router.get("/api/users")
def list_users(request: Request, q: str = "", status: str = "", limit: int = 100, offset: int = 0):
    require_admin(request)
    total, users = user_svc.list_users(q=q, status=status, limit=limit, offset=offset)
    return {"status": "success", "total": total, "users": users}


@router.post("/api/users/reset")
def reset_user(req: UserResetRequest, request: Request):
    require_admin(request)
    openid = (req.openid or "").strip()
    if not openid:
        raise HTTPException(status_code=400, detail="openid 不能为空")
    ok, codes = user_svc.reset_user(openid)
    if not ok:
        raise HTTPException(status_code=404, detail="该用户尚未领取激活码")
    code_str = ", ".join(codes) if codes else ""
    return {"status": "success", "reset": True, "code": code_str, "codes": codes, "message": f"已收回 {openid} 的激活码，其可重新领取"}


@router.post("/api/users/reset-batch")
def reset_users_batch(req: UserBatchResetRequest, request: Request):
    require_admin(request)
    openids = [o.strip() for o in req.openids if o and o.strip()]
    if not openids:
        raise HTTPException(status_code=400, detail="请提供要重置的 openid 列表")
    reset, not_found = user_svc.reset_users_batch(openids)
    return {
        "status": "success",
        "reset": reset,
        "not_found": not_found,
        "message": f"已重置 {len(reset)} 人" + (f"，{len(not_found)} 人无码可收" if not_found else ""),
    }


@router.get("/api/messages")
def list_messages(request: Request, q: str = "", limit: int = 100, offset: int = 0):
    require_admin(request)
    total, messages = message_svc.list_messages(q=q, limit=limit, offset=offset)
    return {"status": "success", "total": total, "messages": messages}


# ----------------- 全局自定义变量 -----------------


@router.get("/api/variables")
def get_variables(request: Request):
    require_admin(request)
    return {"status": "success", "variables": list_custom_variables()}


@router.post("/api/variables")
def create_variable(req: VariableCreateRequest, request: Request):
    require_admin(request)
    k = (req.key or "").strip().lower()
    if not k or len(k) > 32:
        raise HTTPException(status_code=400, detail="变量标识 key 不能为空且最多 32 字")
    import re
    if not re.match(r"^[a-zA-Z0-9_]{1,32}$", k):
        raise HTTPException(status_code=400, detail="变量标识 key 只能由字母、数字和下划线组成")
    var_id = set_custom_variable(k, req.value or "", req.description or "")
    return {"status": "success", "id": var_id}


@router.put("/api/variables/{var_id}")
def update_variable(var_id: int, req: VariableUpdateRequest, request: Request):
    require_admin(request)
    all_vars = {v["id"]: v["key"] for v in list_custom_variables()}
    if var_id not in all_vars:
        raise HTTPException(status_code=404, detail="变量不存在")
    target_key = all_vars[var_id]
    set_custom_variable(target_key, req.value or "", req.description or "")
    return {"status": "success"}


@router.delete("/api/variables/{var_id}")
def remove_variable(var_id: int, request: Request):
    require_admin(request)
    all_vars = {v["id"]: v["key"] for v in list_custom_variables()}
    if var_id not in all_vars:
        raise HTTPException(status_code=404, detail="变量不存在")
    if all_vars[var_id] in ("site", "group"):
        raise HTTPException(status_code=400, detail="系统核心内置变量（site, group）禁止删除，可在列表中直接修改其内容")
    ok = delete_custom_variable(var_id)
    if not ok:
        raise HTTPException(status_code=404, detail="变量不存在")
    return {"status": "success"}


# ----------------- 规则管理 -----------------


@router.get("/api/rules")
def list_rules(request: Request):
    require_admin(request)
    return {"status": "success", "rules": rule_svc.list_rules()}


@router.post("/api/rules")
def create_rule(req: RuleRequest, request: Request):
    require_admin(request)
    rule_id = rule_svc.create_rule(req)
    return {"status": "success", "id": rule_id}


@router.put("/api/rules/{rule_id}")
def update_rule(rule_id: int, req: RuleRequest, request: Request):
    require_admin(request)
    ok = rule_svc.update_rule(rule_id, req)
    if not ok:
        raise HTTPException(status_code=404, detail="规则不存在")
    return {"status": "success"}


@router.delete("/api/rules/{rule_id}")
def delete_rule(rule_id: int, request: Request):
    require_admin(request)
    ok = rule_svc.delete_rule(rule_id)
    if not ok:
        raise HTTPException(status_code=404, detail="规则不存在")
    return {"status": "success"}


@router.post("/api/rules/batch-delete")
def batch_delete_rules(req: RuleBatchDeleteRequest, request: Request):
    require_admin(request)
    ids = [int(i) for i in (req.ids or []) if i > 0]
    if not ids:
        raise HTTPException(status_code=400, detail="请选择要删除的规则")
    count = rule_svc.batch_delete_rules(ids)
    return {"status": "success", "deleted": count}


@router.post("/api/rules/batch-toggle")
def batch_toggle_rules(req: RuleBatchToggleRequest, request: Request):
    require_admin(request)
    ids = [int(i) for i in (req.ids or []) if i > 0]
    if not ids:
        raise HTTPException(status_code=400, detail="请选择要操作的规则")
    count = rule_svc.batch_toggle_rules(ids, req.enabled)
    return {"status": "success", "updated": count}


@router.post("/api/rules/batch-import")
def batch_import_rules(req: RuleBatchImportRequest, request: Request):
    require_admin(request)
    if len(req.rules) > 500:
        raise HTTPException(status_code=400, detail="单次最多导入 500 条规则")
    if req.mode not in ("skip", "overwrite"):
        raise HTTPException(status_code=400, detail="导入模式只能是 skip 或 overwrite")
    return {"status": "success", **rule_svc.batch_import_rules(req.rules, req.mode)}


# ----------------- 系统参数配置 -----------------


@router.get("/api/config")
def get_system_config(request: Request):
    require_admin(request)
    current_token = cs.get_wechat_token()
    return {
        "status": "success",
        "config": {
            "wechat_token": {
                "masked_value": cs.mask_token(current_token),
                "is_set": bool(current_token),
                "from_env": cs.is_wechat_token_from_env(),
                "editable": not cs.is_wechat_token_from_env(),
            },
            "website_url": {
                "value": cs.get_website_url(),
                "from_env": cs.is_website_url_from_env(),
                "editable": not cs.is_website_url_from_env(),
            },
            "group_id": {
                "value": cs.get_group_id(),
                "from_env": cs.is_group_id_from_env(),
                "editable": not cs.is_group_id_from_env(),
            },
            "admin_password": {
                "has_env": bool(config.ADMIN_PASSWORDS),
                "has_db": cs.has_db_admin_password(),
                "editable": True,
            },
        },
    }


@router.put("/api/config")
def update_system_config(req: ConfigUpdateRequest, request: Request):
    require_admin(request)
    config_svc.update_system_config(
        wechat_token=req.wechat_token,
        website_url=req.website_url,
        group_id=req.group_id,
        new_admin_password=req.new_admin_password,
    )
    return {"status": "success", "message": "系统配置更新成功"}
