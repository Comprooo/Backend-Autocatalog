from fastapi import APIRouter, Depends, Query
from typing import Dict, Any, Literal
from app.schemas.common import ResponseModel
from app.services.admin_service import admin_service
from app.core.dependencies import get_current_admin

router = APIRouter(prefix="/admin/stats", tags=["admin_stats"], dependencies=[Depends(get_current_admin)])

@router.get("", response_model=ResponseModel[Dict[str, Any]])
async def get_stats(stats_filter: Literal["mingguan", "bulanan", "tahunan"] = Query(..., alias="filter")):
    stats = await admin_service.get_stats(stats_filter)
    return ResponseModel(data=stats, message="Statistics retrieved successfully")
