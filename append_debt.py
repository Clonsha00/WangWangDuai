content = """
def delete_debts_by_person(person: str, db_path: str = "dms.db") -> None:
    from database import get_connection, DB_PATH
    db_path = db_path if db_path != "dms.db" else DB_PATH
    conn = get_connection(db_path)
    with conn:
        conn.execute("DELETE FROM debts WHERE person = ?", (person,))
    conn.close()
"""
with open('database.py', 'a', encoding='utf-8') as f:
    f.write(content)
