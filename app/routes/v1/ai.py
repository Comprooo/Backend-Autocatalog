from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from typing import List, Any, Optional
from app.schemas.common import ResponseModel
from app.ai.chat import ai_chat_service
from app.core.config import settings
from app.services.car_service import car_service
from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter(prefix="/ai", tags=["ai"])

class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatData(BaseModel):
    reply: str
    car_recommendations: List[Any]
    action: Any = None
    user_role: Optional[str] = None

@router.post("/chat", response_model=ResponseModel[ChatData])
async def chat(request: ChatRequest, current_user: User = Depends(get_current_user)):
    result = await ai_chat_service.get_response(request.message, current_user, request.session_id)
    result["user_role"] = current_user.role
    return ResponseModel(data=result, message="Chat processed")

async def verify_internal_token(x_internal_token: str = Header(...)):
    if x_internal_token != settings.INTERNAL_SERVICE_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid internal token")
    return True

@router.get("/inventory-search", response_model=ResponseModel[List[Any]])
async def internal_inventory_search(
    brand: str = None,
    min_price: float = None,
    max_price: float = None,
    status: str = None,
    token: bool = Depends(verify_internal_token)
):
    cars, _ = await car_service.get_all_cars(
        page=1, limit=50, brand=brand, min_price=min_price, max_price=max_price, status=status
    )
    data = [{"id": str(c.id), "brand": c.brand, "type": c.type, "price": c.price} for c in cars]
    return ResponseModel(data=data, message="Inventory retrieved")
