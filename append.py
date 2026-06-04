content = """
def get_habit_streak(habit_id: int, db_path: str = "dms.db") -> int:
    from database import get_connection, DB_PATH
    db_path = db_path if db_path != "dms.db" else DB_PATH
    conn = get_connection(db_path)
    with conn:
        cur = conn.execute('''
            SELECT date FROM habit_logs 
            WHERE habit_id = ? AND completed = 1 
            ORDER BY date DESC
        ''', (habit_id,))
        rows = cur.fetchall()
    conn.close()
    
    if not rows:
        return 0
        
    streak = 0
    from datetime import date, timedelta
    current = date.today()
    
    if rows[0]["date"] == current.isoformat() or rows[0]["date"] == (current - timedelta(days=1)).isoformat():
        for i, row in enumerate(rows):
            expected_date = current - timedelta(days=i if rows[0]["date"] == current.isoformat() else i + 1)
            if row["date"] == expected_date.isoformat():
                streak += 1
            else:
                break
    return streak

def get_habit_logs_range(habit_id: int, start_date: str, end_date: str, db_path: str = "dms.db") -> list:
    from database import get_connection, DB_PATH
    db_path = db_path if db_path != "dms.db" else DB_PATH
    conn = get_connection(db_path)
    with conn:
        cur = conn.execute('''
            SELECT date, completed FROM habit_logs
            WHERE habit_id = ? AND date >= ? AND date <= ?
            ORDER BY date ASC
        ''', (habit_id, start_date, end_date))
        rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]
"""

with open('database.py', 'a', encoding='utf-8') as f:
    f.write("\n" + content)
