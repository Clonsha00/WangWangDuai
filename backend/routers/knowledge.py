import json
from fastapi import APIRouter, Depends, HTTPException
from models import NodeCreate, NodeUpdate, RelationCreate
from auth import get_current_user
from database import get_db, serialize

router = APIRouter()


@router.get("/nodes")
def list_nodes(search: str = "", _=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        if search:
            cur.execute("""
                SELECT id, title, node_type, updated_at
                FROM knowledge_nodes WHERE title ILIKE %s
                ORDER BY updated_at DESC
            """, (f"%{search}%",))
        else:
            cur.execute("""
                SELECT id, title, node_type, updated_at
                FROM knowledge_nodes ORDER BY updated_at DESC
            """)
        return [serialize(r) for r in cur.fetchall()]


@router.get("/nodes/{node_id}")
def get_node(node_id: int, _=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM knowledge_nodes WHERE id = %s", (node_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "節點不存在")
    return serialize(row)


@router.post("/nodes", status_code=201)
def create_node(body: NodeCreate, _=Depends(get_current_user)):
    props = json.dumps(body.properties or {}, ensure_ascii=False)
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO knowledge_nodes (title, node_type, content, properties)
            VALUES (%s,%s,%s,%s) RETURNING id
        """, (body.title, body.node_type, body.content, props))
        return {"id": cur.fetchone()["id"]}


@router.put("/nodes/{node_id}")
def update_node(node_id: int, body: NodeUpdate, _=Depends(get_current_user)):
    props = json.dumps(body.properties or {}, ensure_ascii=False)
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE knowledge_nodes
            SET title=%s, node_type=%s, content=%s, properties=%s, updated_at=NOW()
            WHERE id=%s
        """, (body.title, body.node_type, body.content, props, node_id))
        if cur.rowcount == 0:
            raise HTTPException(404, "節點不存在")


@router.delete("/nodes/{node_id}", status_code=204)
def delete_node(node_id: int, _=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM knowledge_nodes WHERE id = %s", (node_id,))


@router.get("/nodes/{node_id}/relations")
def forward_relations(node_id: int, _=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT n.id, n.title, n.node_type, r.rel_type, r.id AS relation_id
            FROM relations r
            JOIN knowledge_nodes n ON r.target_id = n.id
            WHERE r.source_id = %s ORDER BY r.created_at ASC
        """, (node_id,))
        return [serialize(r) for r in cur.fetchall()]


@router.get("/nodes/{node_id}/backlinks")
def backlinks(node_id: int, _=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT n.id, n.title, n.node_type, r.rel_type, r.id AS relation_id
            FROM relations r
            JOIN knowledge_nodes n ON r.source_id = n.id
            WHERE r.target_id = %s ORDER BY r.created_at ASC
        """, (node_id,))
        return [serialize(r) for r in cur.fetchall()]


@router.post("/nodes/{node_id}/relations", status_code=201)
def add_relation(node_id: int, body: RelationCreate, _=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO relations (source_id, target_id, rel_type)
            VALUES (%s,%s,%s) ON CONFLICT DO NOTHING
        """, (node_id, body.target_id, body.rel_type))
        return {"created": cur.rowcount > 0}


@router.delete("/nodes/{node_id}/relations/{target_id}", status_code=204)
def delete_relation(node_id: int, target_id: int, _=Depends(get_current_user)):
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM relations WHERE source_id=%s AND target_id=%s",
            (node_id, target_id),
        )
