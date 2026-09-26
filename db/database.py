import json
import os
import sqlite3
from contextlib import contextmanager

import config


def get_db():
    conn = sqlite3.connect(config.DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def db():
    """DB 连接上下文：退出时必关连接，异常不泄漏、不持锁。"""
    conn = get_db()
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    with db() as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=30000")
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS code_pools (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            key TEXT UNIQUE NOT NULL,
            description TEXT DEFAULT '',
            is_default INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_code_pool_key ON code_pools(key)")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            pool_id INTEGER DEFAULT 1,
            status TEXT DEFAULT 'unused',
            assigned_openid TEXT,
            assigned_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_code_claims (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            openid TEXT NOT NULL,
            rule_id INTEGER DEFAULT 0,
            pool_id INTEGER NOT NULL,
            code TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_claim_openid ON user_code_claims(openid)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_claim_rule ON user_code_claims(openid, rule_id)")
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_claim_unique_code ON user_code_claims(code)")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            openid TEXT UNIQUE NOT NULL,
            code TEXT NOT NULL,
            last_event TEXT DEFAULT 'subscribe',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            openid TEXT NOT NULL,
            msg_type TEXT DEFAULT 'text',
            content TEXT,
            reply_content TEXT DEFAULT '',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_code_status ON codes(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_openid ON users(openid)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_msg_openid ON messages(openid)")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_tokens (
            token TEXT PRIMARY KEY,
            expires_at REAL NOT NULL,
            issued_at REAL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        _migrate(cursor)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS keyword_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT NOT NULL,
            mode TEXT DEFAULT 'contains',
            action TEXT DEFAULT 'none',
            content TEXT DEFAULT '',
            priority INTEGER DEFAULT 100,
            enabled INTEGER DEFAULT 1,
            recipe TEXT DEFAULT '',
            status_replies TEXT DEFAULT '',
            start_time TEXT DEFAULT '',
            end_time TEXT DEFAULT '',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS custom_variables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value TEXT NOT NULL,
            description TEXT DEFAULT '',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_var_key ON custom_variables(key)")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS site_settings (
            key TEXT PRIMARY KEY,
            value TEXT DEFAULT ''
        )
        """)
        conn.commit()
        _seed_defaults(cursor)
        conn.commit()


def _migrate(cursor):
    """幂等迁移：老库补列补索引，失败只跳过不中断启动。"""
    try:
        cols = [r[1] for r in cursor.execute("PRAGMA table_info(admin_tokens)").fetchall()]
        if "issued_at" not in cols:
            cursor.execute("ALTER TABLE admin_tokens ADD COLUMN issued_at REAL")
            cursor.execute("UPDATE admin_tokens SET issued_at = expires_at - 86400 WHERE issued_at IS NULL")
    except Exception:
        pass
    try:
        user_cols = [r[1] for r in cursor.execute("PRAGMA table_info(users)").fetchall()]
        if "last_event" not in user_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN last_event TEXT DEFAULT 'subscribe'")
    except Exception:
        pass
    try:
        msg_cols = [r[1] for r in cursor.execute("PRAGMA table_info(messages)").fetchall()]
        if "reply_content" not in msg_cols:
            cursor.execute("ALTER TABLE messages ADD COLUMN reply_content TEXT DEFAULT ''")
    except Exception:
        pass
    try:
        cursor.execute(
            "SELECT code FROM users GROUP BY code HAVING COUNT(*) > 1 LIMIT 1"
        )
        if cursor.fetchone() is None:
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_user_code ON users(code)")
    except Exception:
        pass
    try:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS code_pools (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            key TEXT UNIQUE NOT NULL,
            description TEXT DEFAULT '',
            is_default INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_code_pool_key ON code_pools(key)")
        cursor.execute("INSERT OR IGNORE INTO code_pools (id, name, key, description, is_default) VALUES (1, '默认卡券池', 'default', '系统初始卡券池', 1)")
        pool_cols = [r[1] for r in cursor.execute("PRAGMA table_info(code_pools)").fetchall()]
        if "is_default" not in pool_cols:
            cursor.execute("ALTER TABLE code_pools ADD COLUMN is_default INTEGER DEFAULT 0")
            cursor.execute("UPDATE code_pools SET is_default = 1 WHERE id = 1")
    except Exception:
        pass
    try:
        code_cols = [r[1] for r in cursor.execute("PRAGMA table_info(codes)").fetchall()]
        if "pool_id" not in code_cols:
            cursor.execute("ALTER TABLE codes ADD COLUMN pool_id INTEGER DEFAULT 1")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_code_pool ON codes(pool_id)")
        cursor.execute("UPDATE codes SET pool_id = 1 WHERE pool_id IS NULL")
    except Exception:
        pass
    try:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_code_claims (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            openid TEXT NOT NULL,
            rule_id INTEGER DEFAULT 0,
            pool_id INTEGER NOT NULL,
            code TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_claim_openid ON user_code_claims(openid)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_claim_rule ON user_code_claims(openid, rule_id)")
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_claim_unique_code ON user_code_claims(code)")
        cursor.execute("""
        INSERT INTO user_code_claims (openid, rule_id, pool_id, code, created_at)
        SELECT u.openid, 0, 1, u.code, u.created_at
        FROM users u
        WHERE NOT EXISTS (
            SELECT 1 FROM user_code_claims ucc WHERE ucc.code = u.code
        )
        """)
    except Exception:
        pass
    try:
        rule_cols = [r[1] for r in cursor.execute("PRAGMA table_info(keyword_rules)").fetchall()]
        if "recipe" not in rule_cols:
            cursor.execute("ALTER TABLE keyword_rules ADD COLUMN recipe TEXT DEFAULT ''")
        if "status_replies" not in rule_cols:
            cursor.execute("ALTER TABLE keyword_rules ADD COLUMN status_replies TEXT DEFAULT ''")
        if "start_time" not in rule_cols:
            cursor.execute("ALTER TABLE keyword_rules ADD COLUMN start_time TEXT DEFAULT ''")
        if "end_time" not in rule_cols:
            cursor.execute("ALTER TABLE keyword_rules ADD COLUMN end_time TEXT DEFAULT ''")
    except Exception:
        pass

    try:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS custom_variables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value TEXT NOT NULL,
            description TEXT DEFAULT '',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_var_key ON custom_variables(key)")

        # 迁移或播种基础变量
        cursor.execute("SELECT value FROM site_settings WHERE key = 'website_url'")
        site_val = cursor.fetchone()
        site_url = site_val["value"] if site_val and site_val["value"] else (config.WEBSITE_URL or "https://example.com")
        cursor.execute("INSERT OR IGNORE INTO custom_variables (key, value, description) VALUES ('site', ?, '兑换网站地址')", (site_url,))

        cursor.execute("SELECT value FROM site_settings WHERE key = 'group_id'")
        group_val = cursor.fetchone()
        group_id = group_val["value"] if group_val and group_val["value"] else (config.GROUP_WECHAT_ID or "")
        cursor.execute("INSERT OR IGNORE INTO custom_variables (key, value, description) VALUES ('group', ?, '微信群/客服入口微信号')", (group_id,))
    except Exception:
        pass

    try:
        # 将老欢迎语与兜底回复迁移或确保存在为独立规则
        cursor.execute("SELECT id FROM keyword_rules WHERE action = 'event_subscribe' LIMIT 1")
        if not cursor.fetchone():
            cursor.execute("SELECT value FROM site_settings WHERE key = 'welcome_reply'")
            w_row = cursor.fetchone()
            welcome_tpl = w_row["value"] if w_row and w_row["value"] else ("🎉 欢迎关注！\n\n发送【激活码】，即可获取您的专属激活码（每个用户限领一次）\n\n发送【微信群】，即可获取微信群入口，一起交流！")
            cursor.execute("""
                INSERT INTO keyword_rules (keyword, mode, action, content, priority, enabled)
                VALUES ('__event_subscribe__', 'exact', 'event_subscribe', ?, 1, 1)
            """, (welcome_tpl,))

        cursor.execute("SELECT id FROM keyword_rules WHERE action = 'event_fallback' LIMIT 1")
        if not cursor.fetchone():
            cursor.execute("SELECT value FROM site_settings WHERE key = 'fallback_reply'")
            f_row = cursor.fetchone()
            fallback_tpl = f_row["value"] if f_row and f_row["value"] else ("👋 收到您的留言！\n\n• 发送【激活码】→ 获取专属激活码\n• 发送【微信群】→ 获取微信群入口\n• 每个用户限领一次激活码")
            cursor.execute("""
                INSERT INTO keyword_rules (keyword, mode, action, content, priority, enabled)
                VALUES ('__event_fallback__', 'exact', 'event_fallback', ?, 9999, 1)
            """, (fallback_tpl,))
    except Exception:
        pass

    try:
        # 给历史没有 status_replies 的发码规则补充默认三态文案
        cursor.execute("SELECT id, content FROM keyword_rules WHERE action = 'code' AND (status_replies IS NULL OR status_replies = '')")
        code_rules = cursor.fetchall()
        for cr in code_rules:
            c_content = cr["content"] or "🎉 您的专属激活码为：\n\n【{code}】\n\n👉 兑换地址：{site}\n\n每个用户限领一次，请前往上方兑换地址完成充值兑换！"
            sr = {
                "new": c_content,
                "repeat": "您之前已成功领取过专属激活码：\n\n【{code}】\n\n👉 兑换地址：{site}\n每个用户限领一次，已领取的激活码可随时在上方平台完成兑换！",
                "empty": "抱歉，当前激活码已被领完，请稍后再试或联系管理员！\n平台地址：{site}",
                "not_started": "抱歉，本期激活码领取活动尚未开始，敬请期待！",
                "expired": "抱歉，本期激活码领取活动已经结束，感谢您的关注！",
            }
            cursor.execute("UPDATE keyword_rules SET status_replies = ? WHERE id = ?", (json.dumps(sr, ensure_ascii=False), cr["id"]))
    except Exception:
        pass


def _seed_defaults(cursor):
    """空表时播种默认回复规则与站点设置（复刻内置行为，开箱即用）。"""
    # 播种常用自定义全局变量
    cursor.execute("INSERT OR IGNORE INTO custom_variables (key, value, description) VALUES ('site', ?, '兑换网站地址')", (config.WEBSITE_URL or "https://example.com",))
    cursor.execute("INSERT OR IGNORE INTO custom_variables (key, value, description) VALUES ('group', ?, '微信群/客服入口微信号')", (config.GROUP_WECHAT_ID or "",))

    cursor.execute("SELECT COUNT(*) as n FROM keyword_rules")
    if cursor.fetchone()["n"] == 0:
        welcome_tpl = ("🎉 欢迎关注！\n\n发送【激活码】，即可获取您的专属激活码（每个用户限领一次）\n\n发送【微信群】，即可获取微信群入口，一起交流！")
        fallback_tpl = ("👋 收到您的留言！\n\n• 发送【激活码】→ 获取专属激活码\n• 发送【微信群】→ 获取微信群入口\n• 每个用户限领一次激活码")
        code_tpl = ("🎉 您的专属激活码为：\n\n【{code}】\n\n👉 兑换地址：{site}\n\n每个用户限领一次，请前往上方兑换地址完成充值兑换！")
        group_tpl = ("📱 请添加我的微信号：{group}\n\n添加时备注【进群】，我会拉您进入微信群，一起交流！")

        code_status_replies = json.dumps({
            "new": code_tpl,
            "repeat": "您之前已成功领取过专属激活码：\n\n【{code}】\n\n👉 兑换地址：{site}\n每个用户限领一次，已领取的激活码可随时在上方平台完成兑换！",
            "empty": "抱歉，当前激活码已被领完，请稍后再试或联系管理员！\n平台地址：{site}",
            "not_started": "抱歉，本期激活码领取活动尚未开始，敬请期待！",
            "expired": "抱歉，本期激活码领取活动已经结束，感谢您的关注！",
        }, ensure_ascii=False)

        defaults = [
            ("__event_subscribe__", "exact", "event_subscribe", welcome_tpl, 1, ""),
            ("激活码", "contains", "code", code_tpl, 10, code_status_replies),
            ("激活", "contains", "code", code_tpl, 11, code_status_replies),
            ("兑换码", "contains", "code", code_tpl, 12, code_status_replies),
            ("微信群", "contains", "none", group_tpl, 20, ""),
            ("加群", "contains", "none", group_tpl, 21, ""),
            ("群", "contains", "none", group_tpl, 22, ""),
            ("__event_fallback__", "exact", "event_fallback", fallback_tpl, 9999, ""),
        ]
        for kw, mode, action, content, prio, sr in defaults:
            cursor.execute(
                "INSERT INTO keyword_rules (keyword, mode, action, content, priority, status_replies) VALUES (?, ?, ?, ?, ?, ?)",
                (kw, mode, action, content, prio, sr),
            )
    seed_settings = {
        "new_reply": ("🎉 您的专属激活码为：\n\n【{code}】\n\n"
                        "👉 兑换地址：{site}\n\n每个用户限领一次，请前往上方兑换地址完成充值兑换！"),
        "welcome_reply": ("🎉 欢迎关注！\n\n发送【激活码】，即可获取您的专属激活码"
                            "（每个用户限领一次）\n\n发送【微信群】，即可获取微信群入口，一起交流！"),
        "fallback_reply": ("👋 收到您的留言！\n\n• 发送【激活码】→ 获取专属激活码\n"
                             "• 发送【微信群】→ 获取微信群入口\n• 每个用户限领一次激活码"),
        "repeat_reply": ("您之前已成功领取过专属激活码：\n\n【{code}】\n\n"
                           "👉 兑换地址：{site}\n每个用户限领一次，已领取的激活码可随时在上方平台完成兑换！"),
        "empty_reply": f"抱歉，当前激活码已被领完，请稍后再试或联系管理员！\n平台地址：{config.WEBSITE_URL}",
        "group_id": config.GROUP_WECHAT_ID,
    }
    for k, v in seed_settings.items():
        cursor.execute("INSERT OR IGNORE INTO site_settings (key, value) VALUES (?, ?)", (k, v))
