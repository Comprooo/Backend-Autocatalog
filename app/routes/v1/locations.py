from fastapi import APIRouter, Depends
from typing import List
from app.schemas.location import LocationCreate, LocationResponse
from app.schemas.common import ResponseModel
from app.services.location_service import location_service
from app.core.dependencies import get_current_admin

router = APIRouter(prefix="/locations", tags=["locations"])
admin_router = APIRouter(prefix="/admin/locations", tags=["admin_locations"], dependencies=[Depends(get_current_admin)])

@router.get("", response_model=ResponseModel[List[LocationResponse]])
async def get_locations():
    locations = await location_service.get_all_locations()
    return ResponseModel(data=locations, message="Locations retrieved successfully")

@admin_router.get("", response_model=ResponseModel[List[LocationResponse]])
async def get_admin_locations():
    locations = await location_service.get_all_locations()
    return ResponseModel(data=locations, message="Locations retrieved successfully")

@admin_router.post("", response_model=ResponseModel[LocationResponse])
async def create_location(location_in: LocationCreate):
    location = await location_service.create_location(location_in)
    return ResponseModel(data=location, message="Location created successfully")
