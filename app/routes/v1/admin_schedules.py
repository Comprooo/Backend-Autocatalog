from fastapi import APIRouter, Depends, Query, Path
from typing import List
from app.schemas.schedule import ScheduleResponse, ScheduleStatusUpdate, ScheduleDetailResponse
from app.schemas.common import ResponseModel, PaginatedResponseModel, PaginatedMeta
from app.services.schedule_service import schedule_service
from app.core.dependencies import get_current_admin

router = APIRouter(prefix="/admin/schedules", tags=["admin_schedules"], dependencies=[Depends(get_current_admin)])

@router.get("", response_model=PaginatedResponseModel[List[ScheduleResponse]])
async def get_all_schedules(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100)
):
    schedules, total = await schedule_service.get_all_schedules(page, limit)
    meta = PaginatedMeta(total=total, page=page, limit=limit)
    return PaginatedResponseModel(data=schedules, meta=meta, message="All schedules retrieved successfully")

@router.get("/{schedule_id}", response_model=ResponseModel[ScheduleDetailResponse])
async def get_schedule_detail(schedule_id: str = Path(...)):
    schedule = await schedule_service.get_schedule(schedule_id)
    from app.services.car_service import car_service
    car = await car_service.get_car(str(schedule.car_id))
    
    schedule_data = schedule.model_dump()
    schedule_data["id"] = str(schedule.id)
    schedule_data["user_id"] = str(schedule.user_id)
    schedule_data["car_id"] = str(schedule.car_id)
    schedule_data["car"] = car
    
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
