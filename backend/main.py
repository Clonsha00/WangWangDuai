"""
main.py
-------
FastAPI 應用程式進入點。
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import init_pool
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
    init_pool()


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
