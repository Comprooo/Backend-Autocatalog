from app.repositories.schedule_repo import schedule_repo
from app.services.car_service import car_service
from app.schemas.schedule import ScheduleCreate, ScheduleStatusUpdate
from app.models.user import User
from fastapi import HTTPException
from beanie import PydanticObjectId
from datetime import datetime, timezone, timedelta, time

class ScheduleService:
    async def create_schedule(self, user: User, schedule_in: ScheduleCreate):
        # Business rule: max 2 pending appointments
        pending_count = await schedule_repo.count_pending_for_user(user.id)
        if pending_count >= 2:
            raise HTTPException(status_code=400, detail="Maximum 2 pending appointments allowed")

        # Combine date and time
        try:
            # Expected time format "HH:MM"
            h, m = map(int, schedule_in.time.split(":"))
            scheduled_dt = datetime.combine(schedule_in.schedule_date, time(h, m)).replace(tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid time format. Use HH:MM")

        # Business rule: date must be at least today + 1
        now = datetime.now(timezone.utc)
        tomorrow_start = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        
        if scheduled_dt < tomorrow_start:
            raise HTTPException(status_code=400, detail="Appointment date must be at least H+1 (tomorrow or later)")

        # Verify car exists
        car = await car_service.get_car(schedule_in.car_id)
        
        data = {
            "user_id": user.id,
            "car_id": car.id,
            "date": scheduled_dt,
            "phone": schedule_in.phone,
            "notes": schedule_in.notes,
            "status": "pending"
        }
        return await schedule_repo.create(data)

    async def get_my_schedules(self, user: User, page: int, limit: int):
        skip = (page - 1) * limit
        schedules, total = await schedule_repo.get_by_user(user.id, skip=skip, limit=limit)
        return schedules, total

    async def get_all_schedules(self, page: int, limit: int):
        skip = (page - 1) * limit
        schedules = await schedule_repo.get_all(skip=skip, limit=limit)
        # Using beanie to count all
        total = await schedule_repo.model.find_all().count()
        return schedules, total

    async def get_schedule(self, schedule_id: str):
        if not PydanticObjectId.is_valid(schedule_id):
            raise HTTPException(status_code=400, detail="Invalid ID format")
            
        schedule = await schedule_repo.get(PydanticObjectId(schedule_id))
        if not schedule:
            raise HTTPException(status_code=404, detail="Schedule not found")
        return schedule

    async def cancel_schedule(self, user: User, schedule_id: str):
        schedule = await self.get_schedule(schedule_id)
        if schedule.user_id != user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
        if schedule.status != "pending":
            raise HTTPException(status_code=400, detail="Only pending schedules can be cancelled by customer")
            
        schedule.status = "cancelled"
        await schedule.save()
        return schedule


    async def update_status(self, schedule_id: str, status_update: ScheduleStatusUpdate):
        schedule = await self.get_schedule(schedule_id)
        valid_statuses = ["pending", "confirmed", "cancelled", "completed"]
        if status_update.status not in valid_statuses:
            raise HTTPException(status_code=400, detail="Invalid status")
            
        schedule.status = status_update.status
        await schedule.save()
        return schedule

    async def delete_schedule(self, schedule_id: str):
        schedule = await self.get_schedule(schedule_id)
        await schedule_repo.delete(schedule.id)
        return True

schedule_service = ScheduleService()
