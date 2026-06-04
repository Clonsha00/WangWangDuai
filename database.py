"""
database.py
-----------
雙軌資料庫 Schema：
  - 核心欄位（固定結構）
  - properties（JSON 字串，JSONB 風格擴充欄位）

資料表：
  - transactions      財務紀錄
  - categories        分類標籤
  - actions           行動任務 / 季度目標（GTD）
  - habits            習慣定義
  - habit_logs        每日習慣打卡記錄
  - knowledge_nodes   知識節點（Zettelkasten）
  - relations         節點關聯
  - debts             借款紀錄
"""

import sqlite3
import json
import os
import shutil
from datetime import datetime, date, timedelta
from typing import Optional

# DB 預設放在同目錄下
DB_PATH = os.path.join(os.path.dirname(__file__), "dms.db")

# 不得刪除的預設分類（第一道防線）
PROTECTED_CATEGORY_NAMES: frozenset[str] = frozenset([
    "餐飲", "交通", "購物", "娛樂", "薪資", "其他",
])

# ──────────────────────────────────────────
# 備份機制
# ──────────────────────────────────────────

def auto_backup_db(db_path: str = DB_PATH, retain_days: int = 90) -> None:
    """90 天滾動備份機制"""
    if not os.path.exists(db_path):
        return
        
    backup_dir = os.path.join(os.path.dirname(db_path), "backups")
    os.makedirs(backup_dir, exist_ok=True)
    
    today_date = date.today()
    today_str = today_date.strftime("%Y%m%d")
    base_name = os.path.basename(db_path).split('.')[0]
    backup_file = os.path.join(backup_dir, f"{base_name}_backup_{today_str}.db")
    
    # 1. 每日備份一次
    if not os.path.exists(backup_file):
        shutil.copy2(db_path, backup_file)
        print(f"[Backup] 資料庫已備份至 {backup_file}")
        
    # 2. 清理過期備份
    cutoff_date = today_date - timedelta(days=retain_days)
    for f in os.listdir(backup_dir):
        if f.startswith(f"{base_name}_backup_") and f.endswith(".db"):
            try:
                date_str = f.split("_")[-1].split(".")[0]
                file_date = datetime.strptime(date_str, "%Y%m%d").date()
            except ValueError:
                continue  # 檔名日期解析失敗略過
                
            if file_date < cutoff_date:
                old_file = os.path.join(backup_dir, f)
                try:
                    os.remove(old_file)
                    print(f"[Backup] 已刪除過期備份 {f}")
                except OSError as e:
                    print(f"[Backup] 刪除失敗 {f}: {e}")


# ──────────────────────────────────────────
# 連線工具
# ──────────────────────────────────────────

def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    """取得 SQLite 連線，並啟用 WAL 模式與 FK 約束。"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row          # 讓結果可用欄位名稱存取
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ──────────────────────────────────────────
# Schema 初始化
# ──────────────────────────────────────────

def init_db(db_path: str = DB_PATH) -> None:
    """建立所有資料表（若不存在）。"""
    conn = get_connection(db_path)
    with conn:
        # ---- 分類標籤 ----
        conn.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL UNIQUE,
                icon        TEXT    DEFAULT '🏷️',
                color       TEXT    DEFAULT '#607D8B',
                type        TEXT    NOT NULL DEFAULT 'finance',  -- 'finance'|'note'|'action'
                properties  TEXT    DEFAULT '{}',                -- JSON 擴充欄位
                created_at  TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
        """)

        # ---- 財務紀錄 ----
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                amount       REAL    NOT NULL,
                type         TEXT    NOT NULL DEFAULT 'expense' CHECK(type IN ('income','expense')),
                category_id  INTEGER REFERENCES categories(id) ON DELETE SET NULL,
                description  TEXT    DEFAULT '',
                date         TEXT    NOT NULL DEFAULT (date('now','localtime')),
                properties   TEXT    DEFAULT '{}',
                created_at   TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
        """)



        # ---- 行動任務（GTD 預留）----
        conn.execute("""
            CREATE TABLE IF NOT EXISTS actions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT    NOT NULL,
                status      TEXT    NOT NULL DEFAULT 'todo' CHECK(status IN ('todo','doing','done')),
                priority    INTEGER DEFAULT 2 CHECK(priority IN (1,2,3)),
                due_date    TEXT,
                category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
                properties  TEXT    DEFAULT '{}',
                created_at  TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
                updated_at  TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
        """)

        # ---- 習慣定義 ----
        conn.execute("""
            CREATE TABLE IF NOT EXISTS habits (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT    NOT NULL UNIQUE,
                icon       TEXT    DEFAULT '⚡',
                sort_order INTEGER DEFAULT 0,
                properties TEXT    DEFAULT '{}',
                created_at TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
        """)

        # ---- 每日習慣打卡記錄 ----
        conn.execute("""
            CREATE TABLE IF NOT EXISTS habit_logs (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                habit_id   INTEGER NOT NULL REFERENCES habits(id) ON DELETE CASCADE,
                date       TEXT    NOT NULL DEFAULT (date('now','localtime')),
                completed  INTEGER NOT NULL DEFAULT 0,  -- 0=false 1=true
                created_at TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
                UNIQUE(habit_id, date)
            )
        """)

        # 預設分類（財務）
        defaults = [
            ("餐飲", "🍜", "#E67E22", "finance"),
            ("交通", "🚌", "#3498DB", "finance"),
            ("購物", "🛍️", "#9B59B6", "finance"),
            ("娛樂", "🎮", "#E74C3C", "finance"),
            ("薪資", "💰", "#2ECC71", "finance"),
            ("其他",  "📦", "#95A5A6", "finance"),
        ]
        conn.executemany("""
            INSERT OR IGNORE INTO categories (name, icon, color, type)
            VALUES (?, ?, ?, ?)
        """, defaults)

        # 預設習慣
        default_habits = [
            ("早起",     "🌅", 0),
            ("運動",     "🏃", 1),
            ("閱讀",     "📚", 2),
            ("喝水 2L",  "💧", 3),
            ("冥想",     "🧘", 4),
        ]
        conn.executemany("""
            INSERT OR IGNORE INTO habits (name, icon, sort_order)
            VALUES (?, ?, ?)
        """, default_habits)

        # ---- 知識節點（Zettelkasten）----
        conn.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_nodes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT    NOT NULL,
                node_type   TEXT    NOT NULL DEFAULT 'idea',  -- 'idea'|'journal'|'guide'|'reference'
                content     TEXT    DEFAULT '',
                properties  TEXT    DEFAULT '{}',              -- JSON key-value 擴充欄位
                created_at  TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
                updated_at  TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
            )
        """)

        # ---- 節點關聯 ----
        conn.execute("""
            CREATE TABLE IF NOT EXISTS relations (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id   INTEGER NOT NULL REFERENCES knowledge_nodes(id) ON DELETE CASCADE,
                target_id   INTEGER NOT NULL REFERENCES knowledge_nodes(id) ON DELETE CASCADE,
                rel_type    TEXT    DEFAULT 'link',
                created_at  TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
                UNIQUE(source_id, target_id)
            )
        """)

        # ---- 借款紀錄 (Debts) ----
        conn.execute("""
            CREATE TABLE IF NOT EXISTS debts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                person      TEXT    NOT NULL,
                amount      REAL    NOT NULL CHECK(amount > 0),
                type        TEXT    NOT NULL CHECK(type IN ('lend', 'borrow')),
                status      TEXT    NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'settled')),
                date        TEXT    NOT NULL DEFAULT (date('now','localtime')),
                notes       TEXT    DEFAULT '',
                created_at  TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
                settled_at  TEXT    DEFAULT NULL
            )
        """)

        # Migration: 確保 debts 表有 settled_at 欄位
        cursor = conn.execute("PRAGMA table_info(debts)")
        columns = [row["name"] for row in cursor.fetchall()]
        if "settled_at" not in columns:
            conn.execute("ALTER TABLE debts ADD COLUMN settled_at TEXT DEFAULT NULL")

        # ---- 索引 ----
        conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_habit_logs_date ON habit_logs(date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_actions_priority_status ON actions(priority, status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_debts_status ON debts(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_relations_source ON relations(source_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_relations_target ON relations(target_id)")

    conn.close()
    print(f"[DB] init_db 完成 → {db_path}")


# ──────────────────────────────────────────
# Categories CRUD
# ──────────────────────────────────────────

def get_categories(type_filter: str = "finance", db_path: str = DB_PATH) -> list[dict]:
    conn = get_connection(db_path)
    rows = conn.execute(
        "SELECT * FROM categories WHERE type = ? ORDER BY id", (type_filter,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_category(name: str, icon: str = "🏷️", color: str = "#607D8B",
                 type_: str = "finance", db_path: str = DB_PATH) -> int:
    conn = get_connection(db_path)
    with conn:
        cur = conn.execute(
            "INSERT INTO categories (name, icon, color, type) VALUES (?, ?, ?, ?)",
            (name, icon, color, type_)
        )
    cat_id = cur.lastrowid
    conn.close()
    return cat_id


def delete_category(category_id: int, db_path: str = DB_PATH) -> bool:
    """
    安全刪除分類（單一連線事務）。
    - 若分類名稱在 PROTECTED_CATEGORY_NAMES 中，拋出 ValueError。
    - 若該分類已有歷史交易記錄，拋出 ValueError。
    - 若該分類尚未被使用，執行 DELETE 並回傳 True。
    """
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT name FROM categories WHERE id = ?", (category_id,)
        ).fetchone()

        if row is None:
            return False  # 分類不存在

        cat_name = row["name"]
        if cat_name in PROTECTED_CATEGORY_NAMES:
            raise ValueError(f"「{cat_name}」是系統預設分類，無法刪除")



        with conn:
            cur = conn.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        return cur.rowcount > 0
    finally:
        conn.close()


# ──────────────────────────────────────────
# Transactions CRUD
# ──────────────────────────────────────────

def add_transaction(
    amount: float,
    type_: str = "expense",
    category_id: Optional[int] = None,
    description: str = "",
    date_str: Optional[str] = None,
    extra_props: Optional[dict] = None,
    db_path: str = DB_PATH,
) -> int:
    """新增一筆財務紀錄，回傳新 id。"""
    if date_str is None:
        date_str = date.today().isoformat()
    props = json.dumps(extra_props or {}, ensure_ascii=False)

    conn = get_connection(db_path)
    with conn:
        cur = conn.execute("""
            INSERT INTO transactions (amount, type, category_id, description, date, properties)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (amount, type_, category_id, description, date_str, props))
    tx_id = cur.lastrowid
    conn.close()
    return tx_id


def get_transactions(
    month: Optional[str] = None,       # 格式 "YYYY-MM"
    category_id: Optional[int] = None,
    limit: int = 200,
    db_path: str = DB_PATH,
) -> list[dict]:
    """查詢交易記錄，支援按月份 / 分類篩選。"""
    query = """
        SELECT t.*, c.name AS category_name, c.icon AS category_icon, c.color AS category_color
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE 1=1
    """
    params: list = []
    if month:
        query += " AND strftime('%Y-%m', t.date) = ?"
        params.append(month)
    if category_id is not None:
        query += " AND t.category_id = ?"
        params.append(category_id)
    query += " ORDER BY t.date DESC, t.id DESC LIMIT ?"
    params.append(limit)

    conn = get_connection(db_path)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_transaction(tx_id: int, db_path: str = DB_PATH) -> bool:
    conn = get_connection(db_path)
    with conn:
        cur = conn.execute("DELETE FROM transactions WHERE id = ?", (tx_id,))
    conn.close()
    return cur.rowcount > 0


# ──────────────────────────────────────────
# 統計查詢
# ──────────────────────────────────────────

def get_monthly_summary(month: str, db_path: str = DB_PATH) -> dict:
    """
    回傳指定月份的統計資訊：
    {
        "income": float,
        "expense": float,
        "net": float,
        "by_category": [{"category_name", "icon", "color", "total", "count"}, ...]
    }
    """
    conn = get_connection(db_path)

    totals = conn.execute("""
        SELECT
            COALESCE(SUM(CASE WHEN type='income'  THEN amount ELSE 0 END), 0) AS income,
            COALESCE(SUM(CASE WHEN type='expense' THEN amount ELSE 0 END), 0) AS expense
        FROM transactions
        WHERE strftime('%Y-%m', date) = ?
    """, (month,)).fetchone()

    by_cat = conn.execute("""
        SELECT
            COALESCE(c.name, '未分類')  AS category_name,
            COALESCE(c.icon, '📦')      AS icon,
            COALESCE(c.color, '#95A5A6') AS color,
            SUM(t.amount)               AS total,
            COUNT(*)                    AS count
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE strftime('%Y-%m', t.date) = ?
          AND t.type = 'expense'
        GROUP BY t.category_id
        ORDER BY total DESC
    """, (month,)).fetchall()

    conn.close()
    return {
        "income":      float(totals["income"]),
        "expense":     float(totals["expense"]),
        "net":         float(totals["income"] - totals["expense"]),
        "by_category": [dict(r) for r in by_cat],
    }


def get_monthly_expense_by_category(
    month: str,
    db_path: str = DB_PATH,
) -> list[dict]:
    """
    回傳指定月份的支出分類加總清單，由大到小排序。
    只含 `amount > 0` 的支出項目，不混入收入。
    回傳格式: [{"category_name", "icon", "color", "total"}, ...]
    """
    conn = get_connection(db_path)
    rows = conn.execute("""
        SELECT
            COALESCE(c.name, '未分類')   AS category_name,
            COALESCE(c.icon, '📦')       AS icon,
            COALESCE(c.color, '#95A5A6') AS color,
            SUM(t.amount)               AS total
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE strftime('%Y-%m', t.date) = ?
          AND t.type = 'expense'
          AND t.amount > 0
        GROUP BY t.category_id
        ORDER BY total DESC
    """, (month,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ──────────────────────────────────────────
# Actions CRUD
# ──────────────────────────────────────────

def add_action(
    title: str,
    priority: int = 2,
    due_date: Optional[str] = None,
    category_id: Optional[int] = None,
    db_path: str = DB_PATH,
) -> int:
    """新增一筆任務／目標，回傳新 id。priority: 1=High(季度目標) 2=Normal 3=Low"""
    conn = get_connection(db_path)
    with conn:
        cur = conn.execute("""
            INSERT INTO actions (title, priority, due_date, category_id)
            VALUES (?, ?, ?, ?)
        """, (title, priority, due_date, category_id))
    action_id = cur.lastrowid
    conn.close()
    return action_id


def get_actions(
    priority: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 100,
    db_path: str = DB_PATH,
) -> list[dict]:
    """查詢任務，可按 priority / status 篩選。"""
    query = """
        SELECT a.*, c.name AS category_name, c.color AS category_color
        FROM actions a
        LEFT JOIN categories c ON a.category_id = c.id
        WHERE 1=1
    """
    params: list = []
    if priority is not None:
        query += " AND a.priority = ?"
        params.append(priority)
    if status is not None:
        query += " AND a.status = ?"
        params.append(status)
    query += " ORDER BY a.created_at ASC LIMIT ?"
    params.append(limit)
    conn = get_connection(db_path)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_action_status(
    action_id: int,
    status: str,          # 'todo' | 'doing' | 'done'
    db_path: str = DB_PATH,
) -> bool:
    conn = get_connection(db_path)
    with conn:
        cur = conn.execute("""
            UPDATE actions
            SET status = ?, updated_at = datetime('now','localtime')
            WHERE id = ?
        """, (status, action_id))
    conn.close()
    return cur.rowcount > 0


def delete_action(action_id: int, db_path: str = DB_PATH) -> bool:
    conn = get_connection(db_path)
    with conn:
        cur = conn.execute("DELETE FROM actions WHERE id = ?", (action_id,))
    conn.close()
    return cur.rowcount > 0


def update_todo_due_date(todo_id: int, due_date: Optional[str], db_path: str = DB_PATH) -> bool:
    conn = get_connection(db_path)
    with conn:
        cur = conn.execute("""
            UPDATE actions
            SET due_date = ?, updated_at = datetime('now','localtime')
            WHERE id = ?
        """, (due_date, todo_id))
    conn.close()
    return cur.rowcount > 0


# ──────────────────────────────────────────
# Habits CRUD
# ──────────────────────────────────────────

def get_habits(db_path: str = DB_PATH) -> list[dict]:
    """回傳所有習慣定義，依 sort_order 排序。"""
    conn = get_connection(db_path)
    rows = conn.execute(
        "SELECT * FROM habits ORDER BY sort_order, id"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_habit(name: str, icon: str = "⚡", db_path: str = DB_PATH) -> int:
    conn = get_connection(db_path)
    with conn:
        cur = conn.execute("INSERT INTO habits (name, icon) VALUES (?, ?)", (name, icon))
    habit_id = cur.lastrowid
    conn.close()
    return habit_id

def delete_habit(habit_id: int, db_path: str = DB_PATH) -> bool:
    conn = get_connection(db_path)
    with conn:
        cur = conn.execute("DELETE FROM habits WHERE id = ?", (habit_id,))
    conn.close()
    return cur.rowcount > 0

# ──────────────────────────────────────────
# Debts CRUD
# ──────────────────────────────────────────

def add_debt(person: str, amount: float, type_: str, date_str: str = None, notes: str = "", db_path: str = DB_PATH) -> int:
    person = person.strip()
    if not person:
        raise ValueError("借款對象不能為空")
    if amount <= 0:
        raise ValueError("借款金額必須大於 0")
    if type_ not in ('lend', 'borrow'):
        raise ValueError("借款類別必須是 'lend' 或 'borrow'")

    if date_str is None:
        date_str = date.today().isoformat()

    conn = get_connection(db_path)
    with conn:
        cur = conn.execute("""
            INSERT INTO debts (person, amount, type, date, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (person, amount, type_, date_str, notes))
    debt_id = cur.lastrowid
    conn.close()
    return debt_id

def mark_debt_settled(debt_id: int, db_path: str = DB_PATH) -> bool:
    conn = get_connection(db_path)
    with conn:
        cur = conn.execute("""
            UPDATE debts 
            SET status = 'settled', settled_at = datetime('now','localtime') 
            WHERE id = ? AND status = 'pending'
        """, (debt_id,))
    conn.close()
    return cur.rowcount > 0

def delete_debt(debt_id: int, db_path: str = DB_PATH) -> bool:
    conn = get_connection(db_path)
    with conn:
        cur = conn.execute("DELETE FROM debts WHERE id = ?", (debt_id,))
    conn.close()
    return cur.rowcount > 0

def get_pending_debts(db_path: str = DB_PATH) -> list[dict]:
    conn = get_connection(db_path)
    rows = conn.execute("SELECT * FROM debts WHERE status = 'pending' ORDER BY date DESC, id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_settled_debts(db_path: str = DB_PATH) -> list[dict]:
    conn = get_connection(db_path)
    rows = conn.execute("SELECT * FROM debts WHERE status = 'settled' ORDER BY date DESC, id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_debt_persons(db_path: str = DB_PATH) -> list[str]:
    conn = get_connection(db_path)
    rows = conn.execute("SELECT DISTINCT person FROM debts WHERE person != '' ORDER BY person COLLATE NOCASE").fetchall()
    conn.close()
    return [r[0] for r in rows]

def get_debt_summary_by_person(db_path: str = DB_PATH) -> list[dict]:
    """
    計算每個對象的「淨額」(僅計算 pending 狀態)。
    淨額 = lend 總額 - borrow 總額
    回傳格式: [{"person": str, "net_amount": float}, ...]
    按淨額絕對值大到小排序。
    """
    conn = get_connection(db_path)
    rows = conn.execute("""
        SELECT 
            person,
            SUM(CASE WHEN type = 'lend' THEN amount ELSE 0 END) - 
            SUM(CASE WHEN type = 'borrow' THEN amount ELSE 0 END) AS net_amount
        FROM debts
        WHERE status = 'pending'
        GROUP BY person
        HAVING net_amount != 0
        ORDER BY ABS(net_amount) DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_habit_log_today(
    date_str: Optional[str] = None,
    db_path: str = DB_PATH,
) -> dict[int, bool]:
    """
    回傳今日所有習慣的打卡狀態。
    { habit_id: completed(bool), ... }
    """
    if date_str is None:
        date_str = date.today().isoformat()
    conn = get_connection(db_path)
    rows = conn.execute(
        "SELECT habit_id, completed FROM habit_logs WHERE date = ?",
        (date_str,)
    ).fetchall()
    conn.close()
    return {r["habit_id"]: bool(r["completed"]) for r in rows}


def toggle_habit_log(
    habit_id: int,
    completed: bool,
    date_str: Optional[str] = None,
    db_path: str = DB_PATH,
) -> None:
    """INSERT OR REPLACE 當日習慣打卡狀態（UNIQUE(habit_id, date) 保證唯一）。"""
    if date_str is None:
        date_str = date.today().isoformat()
    conn = get_connection(db_path)
    with conn:
        conn.execute("""
            INSERT INTO habit_logs (habit_id, date, completed)
            VALUES (?, ?, ?)
            ON CONFLICT(habit_id, date) DO UPDATE SET completed = excluded.completed
        """, (habit_id, date_str, int(completed)))
    conn.close()





def get_habits_by_date(date_str: str, db_path: str = DB_PATH) -> list[dict]:
    """查詢特定日期有哪些習慣已經打卡。回傳該日打卡紀錄。"""
    conn = get_connection(db_path)
    rows = conn.execute("""
        SELECT habit_id, completed 
        FROM habit_logs 
        WHERE date = ? AND completed = 1
    """, (date_str,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ──────────────────────────────────────────
# Knowledge Nodes CRUD
# ──────────────────────────────────────────

def add_node(
    title: str,
    node_type: str = "idea",
    content: str = "",
    properties: Optional[dict] = None,
    db_path: str = DB_PATH,
) -> int:
    """新增知識節點，回傳新 id。"""
    props = json.dumps(properties or {}, ensure_ascii=False)
    conn = get_connection(db_path)
    with conn:
        cur = conn.execute("""
            INSERT INTO knowledge_nodes (title, node_type, content, properties)
            VALUES (?, ?, ?, ?)
        """, (title, node_type, content, props))
    node_id = cur.lastrowid
    conn.close()
    return node_id


def get_nodes(search: str = "", db_path: str = DB_PATH) -> list[dict]:
    """列出所有節點（可用標題關鍵字篩選），依 updated_at 倒序。"""
    conn = get_connection(db_path)
    if search:
        rows = conn.execute("""
            SELECT id, title, node_type, updated_at
            FROM knowledge_nodes
            WHERE title LIKE ?
            ORDER BY updated_at DESC
        """, (f"%{search}%",)).fetchall()
    else:
        rows = conn.execute("""
            SELECT id, title, node_type, updated_at
            FROM knowledge_nodes
            ORDER BY updated_at DESC
        """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_node(node_id: int, db_path: str = DB_PATH) -> Optional[dict]:
    """取得單一節點的完整資料（含 properties JSON 字串）。"""
    conn = get_connection(db_path)
    row = conn.execute(
        "SELECT * FROM knowledge_nodes WHERE id = ?", (node_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def update_node(
    node_id: int,
    title: str,
    node_type: str,
    content: str,
    properties: Optional[dict] = None,
    db_path: str = DB_PATH,
) -> bool:
    """更新知識節點內容，同時更新 updated_at。"""
    props = json.dumps(properties or {}, ensure_ascii=False)
    conn = get_connection(db_path)
    with conn:
        cur = conn.execute("""
            UPDATE knowledge_nodes
            SET title=?, node_type=?, content=?, properties=?,
                updated_at=datetime('now','localtime')
            WHERE id=?
        """, (title, node_type, content, props, node_id))
    conn.close()
    return cur.rowcount > 0


def delete_node(node_id: int, db_path: str = DB_PATH) -> bool:
    """刪除節點（CASCADE 自動刪除相關 relations）。"""
    conn = get_connection(db_path)
    with conn:
        cur = conn.execute("DELETE FROM knowledge_nodes WHERE id = ?", (node_id,))
    conn.close()
    return cur.rowcount > 0


# ──────────────────────────────────────────
# Relations CRUD
# ──────────────────────────────────────────

def add_relation(
    source_id: int,
    target_id: int,
    rel_type: str = "link",
    db_path: str = DB_PATH,
) -> bool:
    """新增關聯；若已存在（UNIQUE）則忽略。回傳是否真的新增。"""
    conn = get_connection(db_path)
    with conn:
        cur = conn.execute("""
            INSERT OR IGNORE INTO relations (source_id, target_id, rel_type)
            VALUES (?, ?, ?)
        """, (source_id, target_id, rel_type))
    ok = cur.rowcount > 0
    conn.close()
    return ok


def get_forward_relations(node_id: int, db_path: str = DB_PATH) -> list[dict]:
    """回傳此節點「指向」的其他節點（正向連結）。"""
    conn = get_connection(db_path)
    rows = conn.execute("""
        SELECT n.id, n.title, n.node_type, r.rel_type, r.id AS relation_id
        FROM relations r
        JOIN knowledge_nodes n ON r.target_id = n.id
        WHERE r.source_id = ?
        ORDER BY r.created_at ASC
    """, (node_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_backlinks(node_id: int, db_path: str = DB_PATH) -> list[dict]:
    """回傳「指向此節點」的其他節點（反向連結）。"""
    conn = get_connection(db_path)
    rows = conn.execute("""
        SELECT n.id, n.title, n.node_type, r.rel_type, r.id AS relation_id
        FROM relations r
        JOIN knowledge_nodes n ON r.source_id = n.id
        WHERE r.target_id = ?
        ORDER BY r.created_at ASC
    """, (node_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_relation(source_id: int, target_id: int, db_path: str = DB_PATH) -> bool:
    conn = get_connection(db_path)
    with conn:
        cur = conn.execute(
            "DELETE FROM relations WHERE source_id=? AND target_id=?",
            (source_id, target_id)
        )
    conn.close()
    return cur.rowcount > 0


# ──────────────────────────────────────────
# Update 函式
# ──────────────────────────────────────────

def update_transaction(
    tx_id: int,
    amount: float,
    type_: str,
    category_id: Optional[int],
    description: str,
    date_str: str,
    db_path: str = DB_PATH,
) -> bool:
    """更新一筆交易紀錄，全欄位覆寫。"""
    conn = get_connection(db_path)
    with conn:
        cur = conn.execute("""
            UPDATE transactions
            SET amount=?, type=?, category_id=?, description=?, date=?
            WHERE id=?
        """, (amount, type_, category_id, description, date_str, tx_id))
    conn.close()
    return cur.rowcount > 0


def update_action(
    action_id: int,
    title: Optional[str] = None,
    priority: Optional[int] = None,
    category_id: Optional[int] = None,
    db_path: str = DB_PATH,
) -> bool:
    """部分更新任務欄位（只更新非 None 的參數）。"""
    fields = []
    params: list = []
    if title is not None:
        fields.append("title=?")
        params.append(title)
    if priority is not None:
        fields.append("priority=?")
        params.append(priority)
    if category_id is not None:
        fields.append("category_id=?")
        params.append(category_id)
    if not fields:
        return False
    fields.append("updated_at=datetime('now','localtime')")
    params.append(action_id)
    sql = f"UPDATE actions SET {', '.join(fields)} WHERE id=?"
    conn = get_connection(db_path)
    with conn:
        cur = conn.execute(sql, params)
    conn.close()
    return cur.rowcount > 0


def update_category(
    category_id: int,
    name: Optional[str] = None,
    icon: Optional[str] = None,
    color: Optional[str] = None,
    db_path: str = DB_PATH,
) -> bool:
    """部分更新分類欄位。"""
    fields = []
    params: list = []
    if name is not None:
        fields.append("name=?")
        params.append(name)
    if icon is not None:
        fields.append("icon=?")
        params.append(icon)
    if color is not None:
        fields.append("color=?")
        params.append(color)
    if not fields:
        return False
    params.append(category_id)
    sql = f"UPDATE categories SET {', '.join(fields)} WHERE id=?"
    conn = get_connection(db_path)
    with conn:
        cur = conn.execute(sql, params)
    conn.close()
    return cur.rowcount > 0


def update_habit(
    habit_id: int,
    name: Optional[str] = None,
    icon: Optional[str] = None,
    sort_order: Optional[int] = None,
    db_path: str = DB_PATH,
) -> bool:
    """部分更新習慣欄位。"""
    fields = []
    params: list = []
    if name is not None:
        fields.append("name=?")
        params.append(name)
    if icon is not None:
        fields.append("icon=?")
        params.append(icon)
    if sort_order is not None:
        fields.append("sort_order=?")
        params.append(sort_order)
    if not fields:
        return False
    params.append(habit_id)
    sql = f"UPDATE habits SET {', '.join(fields)} WHERE id=?"
    conn = get_connection(db_path)
    with conn:
        cur = conn.execute(sql, params)
    conn.close()
    return cur.rowcount > 0


# ──────────────────────────────────────────
# 習慣追蹤統計
# ──────────────────────────────────────────

def get_habit_streak(habit_id: int, db_path: str = DB_PATH) -> int:
    """回傳從今天起算的連續打卡天數。若今天未打卡則回傳 0。"""
    conn = get_connection(db_path)
    rows = conn.execute("""
        SELECT date FROM habit_logs
        WHERE habit_id = ? AND completed = 1
        ORDER BY date DESC
    """, (habit_id,)).fetchall()
    conn.close()

    if not rows:
        return 0

    streak = 0
    check_date = date.today()
    for row in rows:
        row_date = date.fromisoformat(row["date"])
        if row_date == check_date:
            streak += 1
            check_date -= timedelta(days=1)
        elif row_date < check_date:
            break  # 斷鏈
    return streak


def get_habit_logs_range(
    habit_id: int,
    start_date: str,
    end_date: str,
    db_path: str = DB_PATH,
) -> list[dict]:
    """回傳指定日期範圍內的習慣打卡記錄。"""
    conn = get_connection(db_path)
    rows = conn.execute("""
        SELECT * FROM habit_logs
        WHERE habit_id = ? AND date >= ? AND date <= ?
        ORDER BY date ASC
    """, (habit_id, start_date, end_date)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ──────────────────────────────────────────
# 測試入口
# ──────────────────────────────────────────

if __name__ == "__main__":
    import tempfile, sys

    # 用暫存 DB 做測試，不汙染正式資料
    tmp_db = os.path.join(tempfile.gettempdir(), "dms_test.db")
    print("=" * 55)
    print(f"  DMS Database 測試  →  {tmp_db}")
    print("=" * 55)

    # 1. 初始化
    init_db(tmp_db)

    # 2. 讀取預設分類
    cats = get_categories(db_path=tmp_db)
    print(f"\n[TEST 1] 預設分類數量：{len(cats)}")
    for c in cats:
        print(f"  {c['icon']}  {c['name']}  ({c['color']})")
    assert len(cats) == 6, "預設分類數量錯誤"

    # 3. 新增自訂分類
    new_cat_id = add_category("健康", "💊", "#1ABC9C", db_path=tmp_db)
    cats2 = get_categories(db_path=tmp_db)
    print(f"\n[TEST 2] 新增分類後數量：{len(cats2)}，新 ID={new_cat_id}")
    assert len(cats2) == 7

    # 4. 新增交易
    meal_cat = next(c for c in cats if c["name"] == "餐飲")
    tx1 = add_transaction(350.0, "expense", meal_cat["id"], "午餐便當", "2026-05-25", db_path=tmp_db)
    tx2 = add_transaction(120.5, "expense", meal_cat["id"], "珍奶",     "2026-05-25", db_path=tmp_db)
    tx3 = add_transaction(50000, "income",  None,           "五月薪資", "2026-05-10", db_path=tmp_db)
    print(f"\n[TEST 3] 新增 3 筆交易，ids = {tx1}, {tx2}, {tx3}")

    # 5. 查詢本月交易
    txs = get_transactions(month="2026-05", db_path=tmp_db)
    print(f"\n[TEST 4] 本月交易筆數：{len(txs)}")
    for t in txs:
        icon = t["category_icon"] or "─"
        print(f"  [{t['date']}] {icon} {t['category_name'] or '未分類':6s}  {t['type']:7s}  NT${t['amount']:,.1f}  {t['description']}")
    assert len(txs) == 3

    # 6. 月份統計
    summary = get_monthly_summary("2026-05", db_path=tmp_db)
    print(f"\n[TEST 5] 2026-05 統計：")
    print(f"  收入:  NT${summary['income']:,.1f}")
    print(f"  支出:  NT${summary['expense']:,.1f}")
    print(f"  淨餘:  NT${summary['net']:,.1f}")
    print(f"  分類明細：")
    for bc in summary["by_category"]:
        print(f"    {bc['icon']} {bc['category_name']:6s}  NT${bc['total']:,.1f}  ({bc['count']} 筆)")
    assert summary["income"] == 50000.0
    assert abs(summary["expense"] - 470.5) < 0.01

    # 7. 刪除一筆
    ok = delete_transaction(tx2, db_path=tmp_db)
    txs2 = get_transactions(month="2026-05", db_path=tmp_db)
    print(f"\n[TEST 6] 刪除 id={tx2} → {ok}，剩餘筆數：{len(txs2)}")
    assert ok and len(txs2) == 2

    # 清理
    os.remove(tmp_db)
    print("\n" + "=" * 55)
    print("  ✅  全部測試通過！")
    print("=" * 55)


def delete_debts_by_person(person: str, db_path: str = DB_PATH) -> None:
    """刪除指定對象的所有借款紀錄（不分 pending/settled）。"""
    conn = get_connection(db_path)
    with conn:
        conn.execute("DELETE FROM debts WHERE person = ?", (person,))
    conn.close()
