from fastapi import APIRouter, Depends, HTTPException, status
from typing import Any
from app.schemas.user import UserCreate, UserLogin, UserResponse, TokenResponse
from app.schemas.common import ResponseModel
from app.services.auth_service import auth_service
from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=ResponseModel[UserResponse])
async def register(user_in: UserCreate):
    user = await auth_service.register(user_in)
    return ResponseModel(data=user, message="User registered successfully")

@router.post("/login", response_model=ResponseModel[TokenResponse])
async def login(login_data: UserLogin):
    token = await auth_service.login(login_data)
    return ResponseModel(data=token, message="Login successful")


@router.post("/logout", response_model=ResponseModel[Any])
async def logout():
    """Logout user (handled client-side by deleting token)."""
    return ResponseModel(message="Logout successful")

@router.get("/me", response_model=ResponseModel[UserResponse])
async def get_me(current_user: User = Depends(get_current_user)):
    return ResponseModel(data=current_user, message="Current user retrieved")
