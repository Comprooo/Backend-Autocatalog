from app.repositories.base import BaseRepository
from app.models.car import Car
from typing import List, Tuple, Optional

class CarRepository(BaseRepository[Car]):
    def __init__(self):
        super().__init__(Car)

    async def get_filtered_cars(
        self,
        skip: int = 0,
        limit: int = 10,
        brand: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        status: Optional[str] = None,
        transmission: Optional[str] = None,
        year: Optional[int] = None,
        car_type: Optional[str] = None
    ) -> Tuple[List[Car], int]:
        
        query = {}
        if brand:
            query["brand"] = {"$regex": brand, "$options": "i"}
        if status:
            query["status"] = status
        if transmission:
            query["transmission"] = {"$regex": transmission, "$options": "i"}
        if year:
            query["year"] = year
        if car_type:
            query["type"] = {"$regex": car_type, "$options": "i"}
            
        if min_price is not None or max_price is not None:
            price_query = {}
            if min_price is not None:
                price_query["$gte"] = min_price
            if max_price is not None:
                price_query["$lte"] = max_price
            query["price"] = price_query

        total = await self.model.find(query).count()
        cars = await self.model.find(query).skip(skip).limit(limit).to_list()
        
        return cars, total

    async def count_by_status(self, status: str) -> int:
        return await self.model.find(self.model.status == status).count()

car_repo = CarRepository()
