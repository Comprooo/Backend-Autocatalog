from fastapi import APIRouter, Depends, Query
from typing import List, Optional
from datetime import date
from app.schemas.available_slot import AvailableSlotCreate, AvailableSlotResponse, AdminAvailableSlotResponse, AvailableSlotUpdate
from app.schemas.common import ResponseModel
from app.services.available_slot_service import available_slot_service
from app.core.dependencies import get_current_admin

router = APIRouter(tags=["available_slots"])

@router.get("/schedules/available", response_model=ResponseModel[List[AvailableSlotResponse]])
async def get_available_slots(
    location_id: Optional[str] = Query(None),
    date: Optional[date] = Query(None)
):
    slots = await available_slot_service.get_available_slots(location_id, date)
    return ResponseModel(data=slots, message="Available slots retrieved successfully")

@router.post("/admin/available-slots", response_model=ResponseModel[AdminAvailableSlotResponse], dependencies=[Depends(get_current_admin)])
async def create_available_slot(slot_in: AvailableSlotCreate):
    slot = await available_slot_service.create_slot(slot_in)
    return ResponseModel(data=slot, message="Available slot created successfully")

@router.patch("/admin/available-slots/{slot_id}", response_model=ResponseModel[AdminAvailableSlotResponse], dependencies=[Depends(get_current_admin)])
async def update_available_slot(slot_id: str, slot_in: AvailableSlotUpdate):
    slot = await available_slot_service.update_slot(slot_id, slot_in)
    return ResponseModel(data=slot, message="Available slot updated successfully")

@router.delete("/admin/available-slots/{slot_id}", response_model=ResponseModel[None], dependencies=[Depends(get_current_admin)])
async def delete_available_slot(slot_id: str):
    await available_slot_service.delete_slot(slot_id)
    return ResponseModel(data=None, message="Available slot deleted successfully")
