from fastapi import APIRouter, Query, Path
from typing import List, Optional
from app.schemas.car import CarResponse
from app.schemas.common import PaginatedResponseModel, PaginatedMeta, ResponseModel
from app.services.car_service import car_service

router = APIRouter(prefix="/cars", tags=["cars"])

@router.get("", response_model=PaginatedResponseModel[List[CarResponse]])
async def get_cars(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    brand: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    status: Optional[str] = Query(None),
    transmission: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    type: Optional[str] = Query(None)
):
    cars, total = await car_service.get_all_cars(
        page=page, limit=limit, brand=brand, min_price=min_price, 
        max_price=max_price, status=status, transmission=transmission, 
        year=year, car_type=type
    )
    meta = PaginatedMeta(total=total, page=page, limit=limit)
    return PaginatedResponseModel(data=cars, meta=meta, message="Cars retrieved successfully")

@router.get("/{car_id}", response_model=ResponseModel[CarResponse])
async def get_car(car_id: str = Path(...)):
    car = await car_service.get_car(car_id)
    return ResponseModel(data=car, message="Car retrieved successfully")
