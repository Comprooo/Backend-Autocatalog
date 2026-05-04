from app.repositories.car_repo import car_repo
from app.schemas.car import CarCreate, CarUpdate, CarStatusUpdate
from fastapi import HTTPException
from beanie import PydanticObjectId

class CarService:
    async def get_all_cars(self, page: int, limit: int, **filters):
        skip = (page - 1) * limit
        cars, total = await car_repo.get_filtered_cars(skip=skip, limit=limit, **filters)
        return cars, total

    async def get_car(self, car_id: str):
        try:
            car = await car_repo.get(PydanticObjectId(car_id))
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid ID format")
        if not car:
            raise HTTPException(status_code=404, detail="Car not found")
        return car

    async def create_car(self, car_in: CarCreate):
        return await car_repo.create(car_in)

    async def update_car(self, car_id: str, car_in: CarUpdate):
        car = await self.get_car(car_id)
        return await car_repo.update(car, car_in)

    async def update_car_status(self, car_id: str, status_in: CarStatusUpdate):
        car = await self.get_car(car_id)
        if status_in.status not in ["Tersedia", "Terjual"]:
            raise HTTPException(status_code=400, detail="Invalid status")
        return await car_repo.update(car, status_in)

    async def delete_car(self, car_id: str):
        car = await self.get_car(car_id)
        return await car_repo.delete(car.id)

car_service = CarService()
