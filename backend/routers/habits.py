from fastapi import APIRouter, Depends
from datetime import date, timedelta
from models import HabitCreate, HabitToggle
from auth import get_current_user
from database import get_db, serialize

router = APIRouter()


@router.get("")
def list_habits(_=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM habits ORDER BY sort_order, id")
        return [serialize(r) for r in cur.fetchall()]


@router.post("", status_code=201)
def create_habit(body: HabitCreate, _=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO habits (name, icon) VALUES (%s,%s) RETURNING id",
            (body.name, body.icon),
        )
        return {"id": cur.fetchone()["id"]}


@router.delete("/{habit_id}", status_code=204)
def delete_habit(habit_id: int, _=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM habits WHERE id = %s", (habit_id,))


@router.get("/logs/today")
def today_logs(_=Depends(get_current_user)):
    today = date.today().isoformat()
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT habit_id, completed FROM habit_logs WHERE date = %s", (today,)
        )
        return {str(r["habit_id"]): bool(r["completed"]) for r in cur.fetchall()}


@router.post("/{habit_id}/toggle")
def toggle_habit(habit_id: int, body: HabitToggle, _=Depends(get_current_user)):
    log_date = (body.date or date.today()).isoformat()
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO habit_logs (habit_id, date, completed)
            VALUES (%s,%s,%s)
            ON CONFLICT (habit_id, date) DO UPDATE SET completed = EXCLUDED.completed
        """, (habit_id, log_date, int(body.completed)))


@router.get("/{habit_id}/streak")
def get_streak(habit_id: int, _=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT date FROM habit_logs
            WHERE habit_id = %s AND completed = 1
            ORDER BY date DESC
        """, (habit_id,))
        rows = cur.fetchall()

    if not rows:
        return {"streak": 0}

    streak = 0
    check = date.today()
    for row in rows:
        row_date = row["date"]
        if row_date == check:
            streak += 1
            check -= timedelta(days=1)
        elif row_date < check:
            break
    return {"streak": streak}
