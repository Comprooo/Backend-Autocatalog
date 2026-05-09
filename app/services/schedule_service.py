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

        # Verify car exists
        car = await car_service.get_car(schedule_in.car_id)
        
        # Verify slot exists and is available
        from app.services.available_slot_service import available_slot_service
        slot = await available_slot_service.get_slot(schedule_in.slot_id)
        
        if slot.booked_count >= slot.quota:
            raise HTTPException(status_code=400, detail="Slot is already full")
        
        # Business rule: date must not be in the past
        now_date = datetime.now(timezone.utc).date()
        if slot.date < now_date:
            raise HTTPException(status_code=400, detail="Cannot book a slot in the past")

        data = {
            "user_id": user.id,
            "car_id": car.id,
            "slot_id": slot.id,
            "notes": schedule_in.notes,
            "status": "pending"
        }
        schedule = await schedule_repo.create(data)
        
        # Update slot booked count
        slot.booked_count += 1
        await slot.save()
        
        return schedule

    async def get_my_schedules(self, user: User, page: int, limit: int):
        skip = (page - 1) * limit
        schedules, total = await schedule_repo.get_by_user(user.id, skip=skip, limit=limit)
        
        # Calculate summary
        pending = await schedule_repo.model.find(schedule_repo.model.user_id == user.id, schedule_repo.model.status == "pending").count()
        confirmed = await schedule_repo.model.find(schedule_repo.model.user_id == user.id, schedule_repo.model.status == "confirmed").count()
        
        from app.schemas.schedule import ScheduleDetailResponse, AppointmentSummary, MyAppointmentsResponse
        from app.schemas.available_slot import AvailableSlotResponse
        from app.models.location import Location
        
        detailed_appointments = []
        for s in schedules:
            car = await car_service.get_car(str(s.car_id))
            from app.models.available_slot import AvailableSlot
            slot_model = await AvailableSlot.get(s.slot_id)
            location = await Location.get(slot_model.location_id) if slot_model else None
            
            s_data = s.model_dump()
            s_data["id"] = str(s.id)
            s_data["user_id"] = str(s.user_id)
            s_data["car_id"] = str(s.car_id)
            s_data["slot_id"] = str(s.slot_id)
            s_data["car"] = car
            s_data["slot"] = AvailableSlotResponse.from_model(slot_model, location) if slot_model else None
            detailed_appointments.append(ScheduleDetailResponse(**s_data))

        return MyAppointmentsResponse(
            summary=AppointmentSummary(total=total, pending=pending, confirmed=confirmed),
            appointments=detailed_appointments
        )

    async def get_all_schedules(self, page: int, limit: int):
        skip = (page - 1) * limit
        schedules = await schedule_repo.get_all(skip=skip, limit=limit)
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
        if schedule.user_id != user.id and user.role != "admin":
            raise HTTPException(status_code=403, detail="Not authorized")
        
        # Allow cancellation if pending or confirmed? 
        # Spec says: "Mengizinkan customer membatalkan pengajuan inspeksi yang masih berstatus pending."
        if user.role != "admin" and schedule.status != "pending":
            raise HTTPException(status_code=400, detail="Only pending schedules can be cancelled by customer")
            
        old_status = schedule.status
        schedule.status = "cancelled"
        await schedule.save()
        
        # If it was pending or confirmed, we should free up the slot
        if old_status in ["pending", "confirmed"]:
            from app.models.available_slot import AvailableSlot
            slot = await AvailableSlot.get(schedule.slot_id)
            if slot and slot.booked_count > 0:
                slot.booked_count -= 1
                await slot.save()
        
        return schedule

    async def update_status(self, schedule_id: str, status_update: ScheduleStatusUpdate):
        schedule = await self.get_schedule(schedule_id)
        valid_statuses = ["pending", "confirmed", "cancelled", "completed"]
        if status_update.status not in valid_statuses:
            raise HTTPException(status_code=400, detail="Invalid status")
            
        old_status = schedule.status
        schedule.status = status_update.status
        await schedule.save()
        
        # If changed to cancelled from active status, free up slot
        if status_update.status == "cancelled" and old_status in ["pending", "confirmed"]:
            from app.models.available_slot import AvailableSlot
            slot = await AvailableSlot.get(schedule.slot_id)
            if slot and slot.booked_count > 0:
                slot.booked_count -= 1
                await slot.save()
        
        return schedule

    async def delete_schedule(self, schedule_id: str):
        schedule = await self.get_schedule(schedule_id)
        
        # Free up slot if active
        if schedule.status in ["pending", "confirmed"]:
            from app.models.available_slot import AvailableSlot
            slot = await AvailableSlot.get(schedule.slot_id)
            if slot and slot.booked_count > 0:
                slot.booked_count -= 1
                await slot.save()
                
        await schedule_repo.delete(schedule.id)
        return True

schedule_service = ScheduleService()


schedule_service = ScheduleService()
