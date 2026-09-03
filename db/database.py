import os
import sqlite3

import config


def get_db():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    conn = get_db()
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
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("SELECT COUNT(*) as cnt FROM codes")
    if cursor.fetchone()["cnt"] == 0:
        default_codes = [
            "482e7b835f764ed68761a63e511e85f2",
            "1d1ecfd5917b40ffbbadcc11dc66e855",
            "84fa282d8c37466ebc24cba43867ffc0",
            "206dcfec337346dcbf0a6538cbfa001c",
            "7068579cf021469ba43b18507ee500f4",
            "4a40643ea3cb4a05a965706536b3f71c",
            "3d4eb896b054452aa8e678396e95bf06",
            "9fc1f919a787408c8955b5de3ab7435a",
            "8d892789d5e649a7ac9906c6ba6d96c7",
            "9c1909fea9084bf2a4df7f123bd1152b"
        ]
        for c in default_codes:
            try:
                cursor.execute("INSERT OR IGNORE INTO codes (code, status) VALUES (?, 'unused')", (c,))
            except Exception:
                pass
    conn.commit()
    conn.close()
