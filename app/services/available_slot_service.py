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
        
        # Masukkan filter ke dalam list
        filters = [
            AvailableSlot.booked_count < AvailableSlot.quota,
            AvailableSlot.date >= today
        ]
        
        if location_id:
            filters.append(AvailableSlot.location_id == PydanticObjectId(location_id))
        if slot_date:
            filters.append(AvailableSlot.date == slot_date)
        
        # Jalankan query dengan membongkar list filters (*filters)
        slots = await AvailableSlot.find(*filters).sort(+AvailableSlot.date, +AvailableSlot.time_start).to_list()
        
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

available_slot_service = AvailableSlotService()
