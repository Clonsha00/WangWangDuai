from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from models import ActionCreate, ActionStatusUpdate, ActionDueDateUpdate
from auth import get_current_user
from database import get_db, serialize

router = APIRouter()


@router.get("")
def list_actions(
    priority: Optional[int] = None,
    status: Optional[str] = None,
    _=Depends(get_current_user),
):
    q = """
        SELECT a.*, c.name AS category_name, c.color AS category_color
        FROM actions a
        LEFT JOIN categories c ON a.category_id = c.id
        WHERE 1=1
    """
    params: list = []
    if priority is not None:
        q += " AND a.priority = %s"; params.append(priority)
    if status is not None:
        q += " AND a.status = %s";   params.append(status)
    q += " ORDER BY a.created_at ASC LIMIT 200"

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(q, params)
        return [serialize(r) for r in cur.fetchall()]


@router.post("", status_code=201)
def create_action(body: ActionCreate, _=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO actions (title, priority, due_date, category_id)
            VALUES (%s,%s,%s,%s) RETURNING id
        """, (body.title, body.priority, body.due_date, body.category_id))
        return {"id": cur.fetchone()["id"]}


@router.patch("/{action_id}/status")
def update_status(action_id: int, body: ActionStatusUpdate, _=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE actions SET status=%s, updated_at=NOW() WHERE id=%s",
            (body.status, action_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(404, "找不到此任務")


@router.patch("/{action_id}/due-date")
def update_due_date(action_id: int, body: ActionDueDateUpdate, _=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE actions SET due_date=%s, updated_at=NOW() WHERE id=%s",
            (body.due_date, action_id),
        )


@router.delete("/{action_id}", status_code=204)
def delete_action(action_id: int, _=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM actions WHERE id = %s", (action_id,))
