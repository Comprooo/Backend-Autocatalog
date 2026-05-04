from fastapi import APIRouter, Depends
from app.schemas.car import CarCreate, CarUpdate, CarStatusUpdate, CarResponse
from app.schemas.common import ResponseModel
from app.services.car_service import car_service
from app.core.dependencies import get_current_admin

router = APIRouter(prefix="/admin/cars", tags=["admin_cars"], dependencies=[Depends(get_current_admin)])

@router.post("", response_model=ResponseModel[CarResponse])
async def create_car(car_in: CarCreate):
    car = await car_service.create_car(car_in)
    return ResponseModel(data=car, message="Car created successfully")

@router.put("/{car_id}", response_model=ResponseModel[CarResponse])
async def update_car(car_id: str, car_in: CarUpdate):
    car = await car_service.update_car(car_id, car_in)
    return ResponseModel(data=car, message="Car updated successfully")

@router.patch("/{car_id}/status", response_model=ResponseModel[CarResponse])
async def update_car_status(car_id: str, status_in: CarStatusUpdate):
    car = await car_service.update_car_status(car_id, status_in)
    return ResponseModel(data=car, message="Car status updated successfully")

@router.delete("/{car_id}", response_model=ResponseModel[str])
async def delete_car(car_id: str):
    await car_service.delete_car(car_id)
    return ResponseModel(data=None, message="Car deleted successfully")
