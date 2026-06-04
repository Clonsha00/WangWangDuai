from fastapi import APIRouter, HTTPException, Depends
from models import LoginRequest, TokenResponse
from auth import authenticate_user, create_token, get_current_user

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest):
    if not authenticate_user(body.username, body.password):
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")
    return TokenResponse(access_token=create_token(body.username))


@router.get("/me")
def me(user: str = Depends(get_current_user)):
    return {"username": user}
