from typing import List
from app.models.location import Location
from app.schemas.location import LocationCreate
from beanie import PydanticObjectId

class LocationService:
    async def create_location(self, location_in: LocationCreate) -> Location:
        location = Location(**location_in.model_dump())
        await location.insert()
        return location

    async def get_all_locations(self) -> List[Location]:
        return await Location.find_all().to_list()

    async def get_location(self, location_id: str) -> Location:
        location = await Location.get(PydanticObjectId(location_id))
        if not location:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Location not found")
        return location

location_service = LocationService()
