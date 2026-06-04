"""
database.py
-----------
PostgreSQL 連線池管理（使用 psycopg3）。
提供 get_db() context manager 供 routers 使用。
"""

import psycopg
import psycopg_pool
from psycopg.rows import dict_row
from contextlib import contextmanager
from config import settings

_pool: psycopg_pool.ConnectionPool | None = None


def init_pool() -> None:
    global _pool
    _pool = psycopg_pool.ConnectionPool(
        conninfo=settings.DATABASE_URL,
        min_size=1,
        max_size=10,
        open=True,
    )


@contextmanager
def get_db():
    """取得連線，自動 commit / rollback / 歸還。"""
    with _pool.connection() as conn:
        conn.row_factory = dict_row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def serialize(row) -> dict:
    """將 psycopg3 dict row 轉為 JSON 可序列化的 dict。"""
    result = {}
    for k, v in dict(row).items():
        if hasattr(v, "isoformat"):
            result[k] = v.isoformat()
        else:
            result[k] = v
    return result
