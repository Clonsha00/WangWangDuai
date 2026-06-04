"""
init_db.py
----------
在第一次部署時執行，建立所有資料表並寫入預設資料。
用法：python init_db.py
"""

import psycopg
from psycopg.rows import dict_row
from passlib.context import CryptContext
from config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    username        TEXT NOT NULL UNIQUE,
    hashed_password TEXT NOT NULL,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS categories (
    id         SERIAL PRIMARY KEY,
    name       TEXT NOT NULL UNIQUE,
    icon       TEXT DEFAULT '🏷️',
    color      TEXT DEFAULT '#607D8B',
    type       TEXT NOT NULL DEFAULT 'finance',
    properties TEXT DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS transactions (
    id          SERIAL PRIMARY KEY,
    amount      REAL NOT NULL,
    type        TEXT NOT NULL DEFAULT 'expense' CHECK(type IN ('income','expense')),
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    description TEXT DEFAULT '',
    date        DATE NOT NULL DEFAULT CURRENT_DATE,
    properties  TEXT DEFAULT '{}',
    created_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS actions (
    id          SERIAL PRIMARY KEY,
    title       TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'todo' CHECK(status IN ('todo','doing','done')),
    priority    INTEGER DEFAULT 2 CHECK(priority IN (1,2,3)),
    due_date    DATE,
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    properties  TEXT DEFAULT '{}',
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS habits (
    id         SERIAL PRIMARY KEY,
    name       TEXT NOT NULL UNIQUE,
    icon       TEXT DEFAULT '⚡',
    sort_order INTEGER DEFAULT 0,
    properties TEXT DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS habit_logs (
    id         SERIAL PRIMARY KEY,
    habit_id   INTEGER NOT NULL REFERENCES habits(id) ON DELETE CASCADE,
    date       DATE NOT NULL DEFAULT CURRENT_DATE,
    completed  INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(habit_id, date)
);

CREATE TABLE IF NOT EXISTS knowledge_nodes (
    id         SERIAL PRIMARY KEY,
    title      TEXT NOT NULL,
    node_type  TEXT NOT NULL DEFAULT 'idea',
    content    TEXT DEFAULT '',
    properties TEXT DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS relations (
    id         SERIAL PRIMARY KEY,
    source_id  INTEGER NOT NULL REFERENCES knowledge_nodes(id) ON DELETE CASCADE,
    target_id  INTEGER NOT NULL REFERENCES knowledge_nodes(id) ON DELETE CASCADE,
    rel_type   TEXT DEFAULT 'link',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(source_id, target_id)
);

CREATE TABLE IF NOT EXISTS debts (
    id         SERIAL PRIMARY KEY,
    person     TEXT NOT NULL,
    amount     REAL NOT NULL CHECK(amount > 0),
    type       TEXT NOT NULL CHECK(type IN ('lend','borrow')),
    status     TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','settled')),
    date       DATE NOT NULL DEFAULT CURRENT_DATE,
    notes      TEXT DEFAULT '',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    settled_at TIMESTAMP DEFAULT NULL
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_transactions_date     ON transactions(date);
CREATE INDEX IF NOT EXISTS idx_habit_logs_date       ON habit_logs(date);
CREATE INDEX IF NOT EXISTS idx_actions_priority      ON actions(priority, status);
CREATE INDEX IF NOT EXISTS idx_debts_status          ON debts(status);
CREATE INDEX IF NOT EXISTS idx_relations_source      ON relations(source_id);
CREATE INDEX IF NOT EXISTS idx_relations_target      ON relations(target_id);
"""

DEFAULT_CATEGORIES = [
    ("餐飲", "🍜", "#E67E22", "finance"),
    ("交通", "🚌", "#3498DB", "finance"),
    ("購物", "🛍️", "#9B59B6", "finance"),
    ("娛樂", "🎮", "#E74C3C", "finance"),
    ("薪資", "💰", "#2ECC71", "finance"),
    ("其他", "📦", "#95A5A6", "finance"),
]

DEFAULT_HABITS = [
    ("早起",    "🌅", 0),
    ("運動",    "🏃", 1),
    ("閱讀",    "📚", 2),
    ("喝水 2L", "💧", 3),
    ("冥想",    "🧘", 4),
]


def init_db() -> None:
    conn = psycopg.connect(settings.DATABASE_URL, row_factory=dict_row)
    try:
        with conn:
            cur = conn.cursor()

            # 建立 Schema
            cur.execute(SCHEMA)

            # 預設分類
            for name, icon, color, type_ in DEFAULT_CATEGORIES:
                cur.execute("""
                    INSERT INTO categories (name, icon, color, type)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (name) DO NOTHING
                """, (name, icon, color, type_))

            # 預設習慣
            for name, icon, order in DEFAULT_HABITS:
                cur.execute("""
                    INSERT INTO habits (name, icon, sort_order)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (name) DO NOTHING
                """, (name, icon, order))

            # 建立管理員帳號（bcrypt 最多 72 bytes，強制截斷）
            safe_pwd = settings.ADMIN_PASSWORD.encode("utf-8")[:72].decode("utf-8", errors="ignore")
            hashed = pwd_context.hash(safe_pwd)
            cur.execute("""
                INSERT INTO users (username, hashed_password)
                VALUES (%s, %s)
                ON CONFLICT (username) DO NOTHING
            """, (settings.ADMIN_USERNAME, hashed))

        print("✅ 資料庫初始化完成！")
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
