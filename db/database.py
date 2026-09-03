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
        CREATE TABLE IF NOT EXISTS codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            status TEXT DEFAULT 'unused',
            assigned_openid TEXT,
            assigned_at DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            openid TEXT UNIQUE NOT NULL,
            code TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            openid TEXT NOT NULL,
            msg_type TEXT DEFAULT 'text',
            content TEXT,
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
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
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
        cursor.execute(
            "SELECT code FROM users GROUP BY code HAVING COUNT(*) > 1 LIMIT 1"
        )
        if cursor.fetchone() is None:
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_user_code ON users(code)")
    except Exception:
        pass


def _seed_defaults(cursor):
    """空表时播种默认回复规则与站点设置（复刻内置行为，开箱即用）。"""
    cursor.execute("SELECT COUNT(*) as n FROM keyword_rules")
    if cursor.fetchone()["n"] == 0:
        code_tpl = ("🎉 您的专属激活码为：\n\n【{code}】\n\n"
                    "👉 兑换地址：{site}\n\n每个用户限领一次，请前往上方兑换地址完成充值兑换！")
        group_tpl = ("📱 请添加我的微信号：{group}\n\n添加时备注【进群】，我会拉您进入微信群，一起交流！")
        defaults = [
            ("激活码", "contains", "code", code_tpl, 10),
            ("激活", "contains", "code", code_tpl, 11),
            ("兑换码", "contains", "code", code_tpl, 12),
            ("微信群", "contains", "none", group_tpl, 20),
            ("加群", "contains", "none", group_tpl, 21),
            ("群", "contains", "none", group_tpl, 22),
        ]
        for kw, mode, action, content, prio in defaults:
            cursor.execute(
                "INSERT INTO keyword_rules (keyword, mode, action, content, priority) VALUES (?, ?, ?, ?, ?)",
                (kw, mode, action, content, prio),
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
