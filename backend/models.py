"""
models.py
---------
所有 Pydantic 請求 / 回應模型。
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import date


# ── Auth ──────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── Categories ────────────────────────────────────────────────────

class CategoryCreate(BaseModel):
    name: str
    icon: str = "🏷️"
    color: str = "#607D8B"
    type: str = "finance"


# ── Transactions ──────────────────────────────────────────────────

class TransactionCreate(BaseModel):
    amount: float = Field(gt=0)
    type: str = "expense"
    category_id: Optional[int] = None
    description: str = ""
    date: Optional[date] = None

class TransactionUpdate(BaseModel):
    amount: float = Field(gt=0)
    type: str
    category_id: Optional[int] = None
    description: str = ""
    date: date


# ── Actions ───────────────────────────────────────────────────────

class ActionCreate(BaseModel):
    title: str
    priority: int = 2
    due_date: Optional[date] = None
    category_id: Optional[int] = None

class ActionStatusUpdate(BaseModel):
    status: str  # 'todo' | 'doing' | 'done'

class ActionDueDateUpdate(BaseModel):
    due_date: Optional[date] = None


# ── Habits ────────────────────────────────────────────────────────

class HabitCreate(BaseModel):
    name: str
    icon: str = "⚡"

class HabitToggle(BaseModel):
    completed: bool
    date: Optional[date] = None


# ── Knowledge ─────────────────────────────────────────────────────

class NodeCreate(BaseModel):
    title: str
    node_type: str = "idea"
    content: str = ""
    properties: Optional[dict] = None

class NodeUpdate(BaseModel):
    title: str
    node_type: str
    content: str
    properties: Optional[dict] = None

class RelationCreate(BaseModel):
    target_id: int
    rel_type: str = "link"


# ── Debts ─────────────────────────────────────────────────────────

class DebtCreate(BaseModel):
    person: str
    amount: float = Field(gt=0)
    type: str  # 'lend' | 'borrow'
    date: Optional[date] = None
    notes: str = ""
