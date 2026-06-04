from fastapi import APIRouter, Depends, HTTPException
from datetime import date
from models import DebtCreate
from auth import get_current_user
from database import get_db, serialize

router = APIRouter()


@router.get("/pending")
def pending_debts(_=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM debts WHERE status='pending' ORDER BY date DESC, id DESC")
        return [serialize(r) for r in cur.fetchall()]


@router.get("/settled")
def settled_debts(_=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM debts WHERE status='settled' ORDER BY date DESC, id DESC")
        return [serialize(r) for r in cur.fetchall()]


@router.get("/summary")
def debt_summary(_=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT person,
                SUM(CASE WHEN type='lend' THEN amount ELSE 0 END) -
                SUM(CASE WHEN type='borrow' THEN amount ELSE 0 END) AS net_amount
            FROM debts WHERE status='pending'
            GROUP BY person
            HAVING SUM(CASE WHEN type='lend' THEN amount ELSE 0 END) -
                   SUM(CASE WHEN type='borrow' THEN amount ELSE 0 END) != 0
            ORDER BY ABS(
                SUM(CASE WHEN type='lend' THEN amount ELSE 0 END) -
                SUM(CASE WHEN type='borrow' THEN amount ELSE 0 END)
            ) DESC
        """)
        return [serialize(r) for r in cur.fetchall()]


@router.get("/persons")
def all_persons(_=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT DISTINCT person FROM debts WHERE person != '' ORDER BY person"
        )
        return [r["person"] for r in cur.fetchall()]


@router.post("", status_code=201)
def create_debt(body: DebtCreate, _=Depends(get_current_user)):
    person = body.person.strip()
    if not person:
        raise HTTPException(400, "借款對象不能為空")
    debt_date = body.date or date.today()
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO debts (person, amount, type, date, notes)
            VALUES (%s,%s,%s,%s,%s) RETURNING id
        """, (person, body.amount, body.type, debt_date, body.notes))
        return {"id": cur.fetchone()["id"]}


@router.patch("/{debt_id}/settle")
def settle_debt(debt_id: int, _=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE debts SET status='settled', settled_at=NOW()
            WHERE id=%s AND status='pending'
        """, (debt_id,))
        if cur.rowcount == 0:
            raise HTTPException(404, "借款不存在或已結清")


@router.delete("/person/{person}", status_code=204)
def delete_person_debts(person: str, _=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM debts WHERE person = %s", (person,))


@router.delete("/{debt_id}", status_code=204)
def delete_debt(debt_id: int, _=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM debts WHERE id = %s", (debt_id,))
