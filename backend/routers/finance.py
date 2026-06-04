from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from datetime import date
from models import TransactionCreate, TransactionUpdate, CategoryCreate
from auth import get_current_user
from database import get_db, serialize

router = APIRouter()

PROTECTED_CATEGORIES = {"餐飲", "交通", "購物", "娛樂", "薪資", "其他"}

# ── Categories ────────────────────────────────────────────────────

@router.get("/categories")
def list_categories(type_filter: str = "finance", _=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM categories WHERE type = %s ORDER BY id", (type_filter,))
        return [serialize(r) for r in cur.fetchall()]


@router.post("/categories", status_code=201)
def create_category(body: CategoryCreate, _=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO categories (name, icon, color, type) VALUES (%s,%s,%s,%s) RETURNING *",
            (body.name, body.icon, body.color, body.type),
        )
        return serialize(cur.fetchone())


@router.delete("/categories/{cat_id}", status_code=204)
def delete_category(cat_id: int, _=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT name FROM categories WHERE id = %s", (cat_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "分類不存在")
        if row["name"] in PROTECTED_CATEGORIES:
            raise HTTPException(400, f"「{row['name']}」是系統預設分類，無法刪除")
        cur.execute("DELETE FROM categories WHERE id = %s", (cat_id,))


# ── Transactions ──────────────────────────────────────────────────

@router.get("/transactions")
def list_transactions(month: Optional[str] = None, _=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        if month:
            cur.execute("""
                SELECT t.*, c.name AS category_name, c.icon AS category_icon, c.color AS category_color
                FROM transactions t
                LEFT JOIN categories c ON t.category_id = c.id
                WHERE TO_CHAR(t.date, 'YYYY-MM') = %s
                ORDER BY t.date DESC, t.id DESC LIMIT 200
            """, (month,))
        else:
            cur.execute("""
                SELECT t.*, c.name AS category_name, c.icon AS category_icon, c.color AS category_color
                FROM transactions t
                LEFT JOIN categories c ON t.category_id = c.id
                ORDER BY t.date DESC, t.id DESC LIMIT 200
            """)
        return [serialize(r) for r in cur.fetchall()]


@router.post("/transactions", status_code=201)
def create_transaction(body: TransactionCreate, _=Depends(get_current_user)):
    tx_date = body.date or date.today()
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO transactions (amount, type, category_id, description, date)
            VALUES (%s,%s,%s,%s,%s) RETURNING id
        """, (body.amount, body.type, body.category_id, body.description, tx_date))
        return {"id": cur.fetchone()["id"]}


@router.put("/transactions/{tx_id}")
def update_transaction(tx_id: int, body: TransactionUpdate, _=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE transactions
            SET amount=%s, type=%s, category_id=%s, description=%s, date=%s
            WHERE id=%s
        """, (body.amount, body.type, body.category_id, body.description, body.date, tx_id))
        if cur.rowcount == 0:
            raise HTTPException(404, "找不到此交易紀錄")


@router.delete("/transactions/{tx_id}", status_code=204)
def delete_transaction(tx_id: int, _=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM transactions WHERE id = %s", (tx_id,))


# ── Statistics ────────────────────────────────────────────────────

@router.get("/summary")
def monthly_summary(month: str, _=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                COALESCE(SUM(CASE WHEN type='income'  THEN amount ELSE 0 END), 0) AS income,
                COALESCE(SUM(CASE WHEN type='expense' THEN amount ELSE 0 END), 0) AS expense
            FROM transactions WHERE TO_CHAR(date, 'YYYY-MM') = %s
        """, (month,))
        totals = cur.fetchone()

        cur.execute("""
            SELECT
                COALESCE(c.name,  '未分類')  AS category_name,
                COALESCE(c.icon,  '📦')      AS icon,
                COALESCE(c.color, '#95A5A6') AS color,
                SUM(t.amount) AS total,
                COUNT(*)      AS count
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE TO_CHAR(t.date, 'YYYY-MM') = %s AND t.type = 'expense'
            GROUP BY t.category_id, c.name, c.icon, c.color
            ORDER BY total DESC
        """, (month,))
        by_cat = cur.fetchall()

    return {
        "income":      float(totals["income"]),
        "expense":     float(totals["expense"]),
        "net":         float(totals["income"] - totals["expense"]),
        "by_category": [serialize(r) for r in by_cat],
    }


@router.get("/stats")
def expense_by_category(month: str, _=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                COALESCE(c.name,  '未分類')  AS category_name,
                COALESCE(c.icon,  '📦')      AS icon,
                COALESCE(c.color, '#95A5A6') AS color,
                SUM(t.amount) AS total
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE TO_CHAR(t.date, 'YYYY-MM') = %s
              AND t.type = 'expense' AND t.amount > 0
            GROUP BY t.category_id, c.name, c.icon, c.color
            ORDER BY total DESC
        """, (month,))
        return [serialize(r) for r in cur.fetchall()]
