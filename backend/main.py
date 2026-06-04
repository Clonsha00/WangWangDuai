"""
main.py
-------
FastAPI 應用程式進入點。
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import init_pool
from init_db import init_db
from routers import auth, finance, actions, habits, knowledge, debts

app = FastAPI(
    title="Daily Management System API",
    version="2.0.0",
    description="DMS 後端 API — 支援財務、行動、習慣、知識庫、借款五大模組",
)

# 允許所有來源（個人使用；正式上線可限縮為你的網域）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    # 只建立連線池（非阻塞），不在啟動時執行 DB 初始化
    # 避免 PostgreSQL 還沒就緒時造成 Railway health check 超時
    init_pool()
    print("✅ 連線池建立完成，服務正在啟動...")


# ── 路由註冊 ──────────────────────────────────────────────────────
app.include_router(auth.router,      prefix="/auth",           tags=["🔑 Auth"])
app.include_router(finance.router,   prefix="/api/finance",    tags=["💰 Finance"])
app.include_router(actions.router,   prefix="/api/actions",    tags=["⚡ Actions"])
app.include_router(habits.router,    prefix="/api/habits",     tags=["🏃 Habits"])
app.include_router(knowledge.router, prefix="/api/knowledge",  tags=["💡 Knowledge"])
app.include_router(debts.router,     prefix="/api/debts",      tags=["💸 Debts"])


@app.get("/health", tags=["System"])
def health():
    return {"status": "ok", "version": "2.0.0"}


@app.get("/admin/debug", tags=["System"])
def debug_env():
    """查看部署時的環境變數實際值（僅除錯用）"""
    from config import settings
    pwd = settings.ADMIN_PASSWORD
    return {
        "admin_username": settings.ADMIN_USERNAME,
        "admin_password_length": len(pwd),
        "admin_password_bytes": len(pwd.encode("utf-8")),
        "admin_password_preview": pwd[:4] + "***" if len(pwd) > 4 else "***",
    }


@app.post("/admin/init-db", tags=["System"])
def manual_init_db():
    """手動觸發資料庫初始化（部署後若自動初始化失敗時使用）"""
    try:
        init_db()
        return {"status": "ok", "message": "資料庫初始化完成"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
