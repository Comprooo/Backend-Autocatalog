from app.schemas.user import UserCreate, UserLogin, TokenResponse
from app.repositories.user_repo import user_repo
from app.core.security import get_password_hash, verify_password, create_access_token
from fastapi import HTTPException, status
from typing import Dict, Any

class AuthService:
    async def register(self, user_in: UserCreate) -> Dict[str, Any]:
        if user_in.password != user_in.password_confirm:
            raise HTTPException(status_code=400, detail="Passwords do not match")
        
        if len(user_in.password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
            
        existing_user = await user_repo.get_by_username(user_in.username)
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already registered")
            
        existing_email = await user_repo.get_by_email(user_in.email)
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already registered")
            
        user_data = user_in.model_dump(exclude={"password_confirm", "password"})
        user_data["hashed_password"] = get_password_hash(user_in.password)
        
        user = await user_repo.create(user_data)
        
        return {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "phone": user.phone,
            "role": user.role,
            "created_at": user.created_at,
            "updated_at": user.updated_at
        }

    async def login(self, login_data: UserLogin) -> TokenResponse:
        user = await user_repo.get_by_username(login_data.username)
        if not user or not verify_password(login_data.password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
            
        access_token = create_access_token(data={"sub": user.username})
        
        return TokenResponse(access_token=access_token, role=user.role)

auth_service = AuthService()
