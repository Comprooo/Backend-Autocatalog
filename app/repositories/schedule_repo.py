from app.repositories.base import BaseRepository
from app.models.schedule import Schedule
from beanie import PydanticObjectId
from typing import List, Tuple, Optional
from datetime import datetime

class ScheduleRepository(BaseRepository[Schedule]):
    def __init__(self):
        super().__init__(Schedule)

    async def count_pending_for_user(self, user_id: PydanticObjectId) -> int:
        return await self.model.find(
            self.model.user_id == user_id,
            self.model.status == "pending"
        ).count()

    async def get_by_user(self, user_id: PydanticObjectId, skip: int = 0, limit: int = 10) -> Tuple[List[Schedule], int]:
        query = self.model.find(self.model.user_id == user_id)
        total = await query.count()
        schedules = await query.skip(skip).limit(limit).to_list()
        return schedules, total

    async def count_by_status(
        self,
        status: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> int:
        query = {"status": status}
        if start_date or end_date:
            created_at_query = {}
            if start_date:
                created_at_query["$gte"] = start_date
            if end_date:
                created_at_query["$lt"] = end_date
            query["created_at"] = created_at_query
            
        return await self.model.find(query).count()

schedule_repo = ScheduleRepository()
