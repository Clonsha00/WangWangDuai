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
    import time
    init_pool()
    # PostgreSQL 在容器環境中需要幾秒才會就緒，最多重試 5 次
    for attempt in range(1, 6):
        try:
            init_db()
            print(f"✅ DB 初始化成功（第 {attempt} 次嘗試）")
            break
        except Exception as e:
            print(f"⚠️  DB 初始化第 {attempt} 次失敗：{e}")
            if attempt < 5:
                time.sleep(3)
            else:
                print("❌ DB 初始化失敗，請手動呼叫 POST /admin/init-db")


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


@app.post("/admin/init-db", tags=["System"])
def manual_init_db():
    """手動觸發資料庫初始化（部署後若自動初始化失敗時使用）"""
    try:
        init_db()
        return {"status": "ok", "message": "資料庫初始化完成"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
