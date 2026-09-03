import time
from collections import defaultdict

from fastapi import HTTPException, Request

import config

# ----------------- 防暴力破解机制 (Anti-Brute-Force) -----------------
login_attempts = defaultdict(lambda: {"count": 0, "lock_until": 0.0, "last_attempt": 0.0})


def get_client_ip(request: Request) -> str:
    # CF Tunnel 部署：只有 cf-connecting-ip 由 Cloudflare 边缘权威写入；
    # x-real-ip / x-forwarded-for 客户端可伪造，一律不采信。
    cf_ip = request.headers.get("cf-connecting-ip")
    if cf_ip:
        return cf_ip.strip()
    return request.client.host if request.client else "127.0.0.1"


def check_rate_limit(ip: str):
    now = time.time()
    info = login_attempts[ip]
    if info["lock_until"] > now:
        remaining = int(info["lock_until"] - now)
        raise HTTPException(
            status_code=429,
            detail=f"密码错误次数过多，您的IP已被临时锁定。请在 {remaining} 秒后重试。"
        )


def record_login_failure(ip: str):
    now = time.time()
    info = login_attempts[ip]
    info["count"] += 1
    info["last_attempt"] = now
    if info["count"] >= config.MAX_FAILED_ATTEMPTS:
        info["lock_until"] = now + config.LOCKOUT_DURATION
        remaining = int(info["lock_until"] - now)
        raise HTTPException(
            status_code=429,
            detail=f"连续输错密码达到上限，您的IP已被锁定15分钟。请在 {remaining} 秒后重试。"
        )


def record_login_success(ip: str):
    if ip in login_attempts:
        del login_attempts[ip]


# ----------------- 微信入口节流 -----------------
_wechat_hits = defaultdict(list)


def check_wechat_throttle(ip: str) -> bool:
    """每 IP 每分钟至多 WECHAT_RATE_PER_MIN 次，超限返回 False。"""
    now = time.time()
    window_start = now - 60
    hits = [t for t in _wechat_hits[ip] if t > window_start]
    if len(hits) >= config.WECHAT_RATE_PER_MIN:
        _wechat_hits[ip] = hits
        return False
    hits.append(now)
    _wechat_hits[ip] = hits
    return True


def normalize_pwd(pwd: str) -> tuple:
    if not pwd:
        return "", "", ""
    p = pwd.strip()
    p_cn = p.replace("!", "！")
    p_en = p.replace("！", "!")
    return p, p_cn, p_en


def is_valid_pwd(pwd: str) -> bool:
    if not pwd:
        return False
    p, p_cn, p_en = normalize_pwd(pwd)
    for check in [p, p_cn, p_en]:
        if check in config.ADMIN_PASSWORDS:
            return True
    return False
