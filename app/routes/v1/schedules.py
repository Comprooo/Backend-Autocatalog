from fastapi import APIRouter, Depends, Query, Path
from typing import List
from app.schemas.schedule import ScheduleCreate, ScheduleResponse, ScheduleDetailResponse
from app.schemas.common import ResponseModel, PaginatedResponseModel, PaginatedMeta
from app.services.schedule_service import schedule_service
from app.core.dependencies import get_current_customer
from app.models.user import User

router = APIRouter(prefix="/schedules", tags=["schedules"], dependencies=[Depends(get_current_customer)])

@router.post("", response_model=ResponseModel[ScheduleResponse])
async def create_schedule(schedule_in: ScheduleCreate, current_user: User = Depends(get_current_customer)):
    schedule = await schedule_service.create_schedule(current_user, schedule_in)
    return ResponseModel(data=schedule, message="Schedule created successfully")

@router.get("/me", response_model=PaginatedResponseModel[List[ScheduleResponse]])
async def get_my_schedules(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_customer)
):
    schedules, total = await schedule_service.get_my_schedules(current_user, page, limit)
    meta = PaginatedMeta(total=total, page=page, limit=limit)
    return PaginatedResponseModel(data=schedules, meta=meta, message="Schedules retrieved successfully")

@router.get("/{schedule_id}", response_model=ResponseModel[ScheduleDetailResponse])
async def get_schedule(schedule_id: str = Path(...), current_user: User = Depends(get_current_customer)):
    schedule = await schedule_service.get_schedule(schedule_id)
    
    # Check if belongs to user
    if schedule.user_id != current_user.id and current_user.role != "admin":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Not authorized")
    
    from app.services.car_service import car_service
    car = await car_service.get_car(str(schedule.car_id))
    
    # We combine schedule data and car data into a dictionary for the response model
    schedule_data = schedule.model_dump()
    schedule_data["id"] = str(schedule.id)
    schedule_data["user_id"] = str(schedule.user_id)
    schedule_data["car_id"] = str(schedule.car_id)
    schedule_data["car"] = car
    
    return ResponseModel(data=ScheduleDetailResponse(**schedule_data), message="Schedule retrieved successfully")


@router.patch("/{schedule_id}/cancel", response_model=ResponseModel[ScheduleResponse])
async def cancel_schedule(schedule_id: str = Path(...), current_user: User = Depends(get_current_customer)):
    schedule = await schedule_service.cancel_schedule(current_user, schedule_id)
    return ResponseModel(data=schedule, message="Schedule cancelled successfully")


