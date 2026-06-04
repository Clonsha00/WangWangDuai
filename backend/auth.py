"""
auth.py
-------
JWT 登入驗證。
個人使用：單一管理員帳號，token 有效期 7 天。
"""

from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from config import settings
from database import get_db, serialize

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", truncate_error=False)
_bearer = HTTPBearer()


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_token(username: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": username, "exp": expire},
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )


def authenticate_user(username: str, password: str) -> bool:
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT hashed_password FROM users WHERE username = %s", (username,))
        row = cur.fetchone()
    if not row:
        return False
    return verify_password(password, row["hashed_password"])


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(_bearer)) -> str:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Token 無效或已過期，請重新登入")
