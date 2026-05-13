from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from app.core.config import settings
from app.models.user import User

bearer_scheme = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> User:
    from beanie import PydanticObjectId
    token = credentials.credentials
    try:
        # Tambahkan leeway (toleransi) 60 detik untuk sinkronisasi waktu
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=[settings.JWT_ALGORITHM],
            options={"leeway": 60}
        )
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if user_id is None or token_type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        user = await User.get(PydanticObjectId(user_id))
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # ─── INACTIVITY TIMEOUT LOGIC (3 Hours) ───
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        
        # Pastikan last_activity punya info timezone UTC untuk dibandingkan
        last_act = user.last_activity
        if last_act and last_act.tzinfo is None:
            last_act = last_act.replace(tzinfo=timezone.utc)

        # Jika user sudah tidak aktif lebih dari 3 jam
        if last_act and (now - last_act) > timedelta(hours=3):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired due to inactivity (3 hours). Please login again.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Update last_activity (kita update tiap minimal 1 menit agar tidak terlalu membebani DB)
        if not last_act or (now - last_act) > timedelta(minutes=1):
            user.last_activity = now
            await user.save()
            
        return user

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please login again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        # Tampilkan error asli di log server untuk debugging
        import logging
        logging.error(f"AUTH ERROR: {str(e)}")
        
        # Berikan pesan yang sedikit lebih detail jika itu bukan masalah JWT
        error_msg = "Could not validate credentials"
        if "User not found" in str(e):
            error_msg = "User in token no longer exists. Please login again."
            
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_msg,
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

async def get_current_customer(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in ["customer", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user
