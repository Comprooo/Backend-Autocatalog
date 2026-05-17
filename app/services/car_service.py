from app.repositories.car_repo import car_repo
from app.schemas.car import CarCreate, CarUpdate, CarStatusUpdate
from fastapi import HTTPException
from beanie import PydanticObjectId

class CarService:
    async def get_all_cars(self, page: int, limit: int, **filters):
        skip = (page - 1) * limit
        cars, total = await car_repo.get_filtered_cars(skip=skip, limit=limit, **filters)
        stats = await car_repo.get_car_stats()
        return cars, total, stats

    async def get_car(self, car_id: str):
        try:
            car = await car_repo.get(PydanticObjectId(car_id))
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid ID format")
        if not car:
            raise HTTPException(status_code=404, detail="Car not found")
        return car

    async def create_car(self, car_in: CarCreate):
        # Flatten specifications
        specs = car_in.specifications
        # Parse mileage "45000 km" -> 45000
        mileage_int = 0
        try:
            mileage_int = int(''.join(filter(str.isdigit, specs.mileage)))
        except ValueError:
            pass

        car_dict = {
            "brand": car_in.brand,
            "model": car_in.model,
            "price": car_in.price,
            "condition": car_in.condition,
            "year": specs.year,
            "transmission": specs.transmission,
            "mileage": mileage_int,
            "fuel": specs.fuel,
            "color": specs.color,
            "car_type": specs.type,
            "description": car_in.description,
            "features": car_in.features,
            "images": car_in.images,
            "status": "Tersedia"
        }
        from app.models.car import Car
        car = Car(**car_dict)
        await car.insert()
        return car

    async def update_car(self, car_id: str, car_in: CarUpdate):
        car = await self.get_car(car_id)
        update_data = car_in.model_dump(exclude_unset=True)
        
        if "specifications" in update_data:
            specs = update_data.pop("specifications")
            if "year" in specs: update_data["year"] = specs["year"]
            if "transmission" in specs: update_data["transmission"] = specs["transmission"]
            if "color" in specs: update_data["color"] = specs["color"]
            if "fuel" in specs: update_data["fuel"] = specs["fuel"]
            if "type" in specs: update_data["car_type"] = specs["type"]
            if "mileage" in specs:
                try:
                    update_data["mileage"] = int(''.join(filter(str.isdigit, specs["mileage"])))
                except ValueError:
                    pass
        
        if "status" in update_data:
            new_status = update_data["status"]
            if new_status == "Terjual" and car.status != "Terjual":
                from datetime import datetime, timezone
                car.sold_at = datetime.now(timezone.utc)
            elif new_status == "Tersedia" and car.status != "Tersedia":
                car.sold_at = None

        for field, value in update_data.items():
            setattr(car, field, value)
        
        await car.save()
        return car

    async def update_car_status(self, car_id: str, status_in: CarStatusUpdate):
        car = await self.get_car(car_id)
        if status_in.status not in ["Tersedia", "Terjual"]:
            raise HTTPException(status_code=400, detail="Invalid status")
        
        if status_in.status == "Terjual" and car.status != "Terjual":
            from datetime import datetime, timezone
            car.sold_at = datetime.now(timezone.utc)
        elif status_in.status == "Tersedia" and car.status != "Tersedia":
            car.sold_at = None

        return await car_repo.update(car, {"status": status_in.status, "sold_at": car.sold_at})

    async def delete_car(self, car_id: str):
        car = await self.get_car(car_id)
        return await car_repo.delete(car.id)

car_service = CarService()
