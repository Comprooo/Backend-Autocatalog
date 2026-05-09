from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from typing import List, Any, Optional
from app.schemas.common import ResponseModel
from app.ai.chat import ai_chat_service
from app.core.config import settings
from app.services.car_service import car_service
from app.core.dependencies import get_current_user
from app.models.user import User

chat_router = APIRouter(tags=["chat"])
ai_router = APIRouter(prefix="/ai", tags=["ai"])

class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatData(BaseModel):
    reply: str
    car_recommendations: List[Any]

@chat_router.post("/chat", response_model=ResponseModel[ChatData])
async def chat(request: ChatRequest, current_user: User = Depends(get_current_user)):
    result = await ai_chat_service.get_response(request.message, current_user, request.session_id)
    # result["user_role"] = current_user.role # Not in spec, but could be useful
    return ResponseModel(data=ChatData(**result), message="Chat processed")

async def verify_internal_token(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    
    token = authorization.split(" ")[1]
    if token != settings.INTERNAL_SERVICE_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid internal token")
    return True

@ai_router.get("/inventory-search", response_model=ResponseModel[List[Any]])
async def internal_inventory_search(
    brand: str = None,
    min_price: float = None,
    max_price: float = None,
    status: str = None,
    authenticated: bool = Depends(verify_internal_token)
):
    cars, _ = await car_service.get_all_cars(
        page=1, limit=50, brand=brand, min_price=min_price, max_price=max_price, status=status
    )
    # Match the spec response
    data = [
        {
            "car_id": str(c.id), 
            "brand": c.brand, 
            "model": c.model if hasattr(c, "model") else c.type, 
            "price": c.price,
            "status": c.status,
            "thumbnail_url": c.images[0] if c.images else ""
        } for c in cars
    ]
    return ResponseModel(data=data, message="Inventory retrieved")
