from app.repositories.car_repo import car_repo
from app.repositories.schedule_repo import schedule_repo
from typing import Dict, Any, Optional

class AdminService:
    async def get_stats(self, year: Optional[int] = None) -> Dict[str, Any]:
        available_cars = await car_repo.count_by_status("Tersedia", year)
        sold_cars = await car_repo.count_by_status("Terjual", year)
        
        pending_schedules = await schedule_repo.count_by_status("pending", year)
        confirmed_schedules = await schedule_repo.count_by_status("confirmed", year)
        cancelled_schedules = await schedule_repo.count_by_status("cancelled", year)
        
        return {
            "inventory": {
                "available": available_cars,
                "sold": sold_cars
            },
            "appointments": {
                "pending": pending_schedules,
                "confirmed": confirmed_schedules
            }
        }

admin_service = AdminService()
