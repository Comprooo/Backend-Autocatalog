from typing import List, Optional
from datetime import date
from app.models.available_slot import AvailableSlot
from app.models.location import Location
from app.schemas.available_slot import AvailableSlotCreate, AvailableSlotResponse
from beanie import PydanticObjectId

class AvailableSlotService:
    async def create_slot(self, slot_in: AvailableSlotCreate) -> AvailableSlot:
        # Verify location exists
        location = await Location.get(PydanticObjectId(slot_in.location_id))
        if not location:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Location not found")
        
        slot = AvailableSlot(
            location_id=PydanticObjectId(slot_in.location_id),
            date=slot_in.date,
            time_start=slot_in.time_start,
            time_end=slot_in.time_end,
            quota=slot_in.quota
        )
        await slot.insert()
        return slot

    async def get_available_slots(self, location_id: Optional[str] = None, slot_date: Optional[date] = None) -> List[AvailableSlotResponse]:
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).date()
        
        # Menggunakan $expr untuk perbandingan antar field agar lebih akurat di MongoDB
        filters = [
            {"$expr": {"$lt": ["$booked_count", "$quota"]}},
            AvailableSlot.date >= today
        ]
        
        if location_id:
            filters.append(AvailableSlot.location_id == PydanticObjectId(location_id))
        if slot_date:
            filters.append(AvailableSlot.date == slot_date)
        
        # Jalankan query
        slots = await AvailableSlot.find(*filters).sort(+AvailableSlot.date, +AvailableSlot.time_start).to_list()
        
        # Debug log (bisa dihapus nanti)
        print(f"DEBUG: Found {len(slots)} slots for today ({today}) onwards")
        
        # Load locations for response
        location_ids = list(set([s.location_id for s in slots]))
        locations = await Location.find({"_id": {"$in": location_ids}}).to_list()
        location_map = {str(l.id): l for l in locations}
        
        return [AvailableSlotResponse.from_model(s, location_map.get(str(s.location_id))) for s in slots]

    async def get_slot(self, slot_id: str) -> AvailableSlot:
        slot = await AvailableSlot.get(PydanticObjectId(slot_id))
        if not slot:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Available slot not found")
        return slot

    async def update_slot(self, slot_id: str, slot_in: "AvailableSlotUpdate") -> AvailableSlot:
        slot = await self.get_slot(slot_id)
        from datetime import datetime, timezone
        from fastapi import HTTPException
        
        if slot_in.location_id is not None:
            # Verify new location exists
            location = await Location.get(PydanticObjectId(slot_in.location_id))
            if not location:
                raise HTTPException(status_code=404, detail="Location not found")
            slot.location_id = PydanticObjectId(slot_in.location_id)
            
        if slot_in.date is not None:
            from datetime import datetime
            try:
                slot.date = datetime.strptime(slot_in.date, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format, must be YYYY-MM-DD")
            
        if slot_in.time_start is not None:
            slot.time_start = slot_in.time_start
            
        if slot_in.time_end is not None:
            slot.time_end = slot_in.time_end
            
        if slot_in.quota is not None:
            if slot_in.quota < slot.booked_count:
                raise HTTPException(status_code=400, detail="Quota cannot be less than booked count")
            slot.quota = slot_in.quota
            
        slot.updated_at = datetime.now(timezone.utc)
        await slot.save()
        return slot

    async def delete_slot(self, slot_id: str) -> bool:
        slot = await self.get_slot(slot_id)
        from fastapi import HTTPException
        
        if slot.booked_count > 0:
            raise HTTPException(status_code=400, detail="Cannot delete a slot that already has bookings")
            
        await slot.delete()
        return True

available_slot_service = AvailableSlotService()
