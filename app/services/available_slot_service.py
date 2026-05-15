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

    async def generate_default_slots(self, days_ahead: int = 14):
        """Otomatis membuat slot kosong jika belum ada untuk 14 hari ke depan."""
        from datetime import datetime, timezone, timedelta
        from app.models.location import Location
        
        today = datetime.now(timezone.utc).date()
        locations = await Location.find_all().to_list()
        
        # Template jam kerja (9 pagi - 5 sore)
        work_hours = [
            ("09:00", "10:00"), ("10:00", "11:00"), ("11:00", "12:00"),
            ("13:00", "14:00"), ("14:00", "15:00"), ("15:00", "16:00"), ("16:00", "17:00")
        ]

        created_count = 0
        for i in range(days_ahead):
            target_date = today + timedelta(days=i)
            for loc in locations:
                for start, end in work_hours:
                    # Cek apakah slot sudah ada
                    exists = await AvailableSlot.find_one(
                        AvailableSlot.location_id == loc.id,
                        AvailableSlot.date == target_date,
                        AvailableSlot.time_start == start
                    )
                    
                    if not exists:
                        new_slot = AvailableSlot(
                            location_id=loc.id,
                            date=target_date,
                            time_start=start,
                            time_end=end,
                            quota=1, # Eksklusif 1 orang
                            booked_count=0
                        )
                        await new_slot.insert()
                        created_count += 1
        
        if created_count > 0:
            print(f"AUTO-GEN: Created {created_count} new available slots for the next {days_ahead} days.")

available_slot_service = AvailableSlotService()
