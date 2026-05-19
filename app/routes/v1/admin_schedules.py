from fastapi import APIRouter, Depends, Query, Path
from typing import List
from app.schemas.schedule import ScheduleResponse, ScheduleStatusUpdate, ScheduleDetailResponse, MyAppointmentsResponse
from app.schemas.common import ResponseModel, PaginatedResponseModel, PaginatedMeta
from app.services.schedule_service import schedule_service
from app.core.dependencies import get_current_admin

router = APIRouter(prefix="/admin/schedules", tags=["admin_schedules"], dependencies=[Depends(get_current_admin)])

@router.get("", response_model=ResponseModel[MyAppointmentsResponse])
async def get_all_schedules(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100)
):
    result = await schedule_service.get_admin_schedules(page, limit)
    return ResponseModel(data=result, message="All schedules retrieved successfully")

@router.get("/{schedule_id}", response_model=ResponseModel[ScheduleDetailResponse])
async def get_schedule_detail(schedule_id: str = Path(...)):
    schedule = await schedule_service.get_schedule(schedule_id)
    from app.repositories.car_repo import car_repo
    from app.schemas.car import CarResponse
    car = await car_repo.get(schedule.car_id)
    
    from app.models.available_slot import AvailableSlot
    from app.models.location import Location
    from app.schemas.available_slot import AvailableSlotResponse
    
    slot_model = await AvailableSlot.get(schedule.slot_id)
    location = await Location.get(slot_model.location_id) if slot_model else None
    
    schedule_data = schedule.model_dump()
    schedule_data["id"] = str(schedule.id)
    schedule_data["user_id"] = str(schedule.user_id)
    schedule_data["car_id"] = str(schedule.car_id)
    schedule_data["slot_id"] = str(schedule.slot_id)
    from app.models.user import User as UserModel
    from app.schemas.user import UserResponse
    user_model = await UserModel.get(schedule.user_id)
    schedule_data["car"] = CarResponse.from_model(car) if car else None
    schedule_data["slot"] = AvailableSlotResponse.from_model(slot_model, location) if slot_model else None
    schedule_data["user"] = UserResponse.model_validate(user_model) if user_model else None
    
    return ResponseModel(data=ScheduleDetailResponse(**schedule_data), message="Schedule detail retrieved")

@router.patch("/{schedule_id}/status", response_model=ResponseModel[ScheduleResponse])
async def update_schedule_status(schedule_id: str, status_update: ScheduleStatusUpdate):
    schedule = await schedule_service.update_status(schedule_id, status_update)
    return ResponseModel(data=schedule, message="Schedule status updated")

@router.patch("/{schedule_id}/reject", response_model=ResponseModel[ScheduleResponse])
async def reject_schedule(schedule_id: str = Path(...)):
    """Convenience endpoint for admin to reject an appointment."""
    status_update = ScheduleStatusUpdate(status="cancelled")
    schedule = await schedule_service.update_status(schedule_id, status_update)
    return ResponseModel(data=schedule, message="Appointment rejected successfully")

@router.delete("/{schedule_id}", response_model=ResponseModel[str])
async def delete_schedule(schedule_id: str = Path(...)):
    """Admin endpoint to permanently delete an appointment."""
    await schedule_service.delete_schedule(schedule_id)
    return ResponseModel(data=None, message="Schedule deleted successfully by Admin")
