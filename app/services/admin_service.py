from app.repositories.car_repo import car_repo
from app.repositories.schedule_repo import schedule_repo
from typing import Dict, Any

class AdminService:
    async def get_stats(self) -> Dict[str, Any]:
        available_cars = await car_repo.count_by_status("Tersedia")
        sold_cars = await car_repo.count_by_status("Terjual")
        
        pending_schedules = await schedule_repo.count_by_status("pending")
        confirmed_schedules = await schedule_repo.count_by_status("confirmed")
        cancelled_schedules = await schedule_repo.count_by_status("cancelled")
        
        return {
            "inventory_summary": {
                "available": available_cars,
                "sold": sold_cars
            },
            "appointment_summary": {
                "pending": pending_schedules,
                "confirmed": confirmed_schedules,
                "cancelled": cancelled_schedules
            }
        }

admin_service = AdminService()
