from app.repositories.car_repo import car_repo
from app.repositories.schedule_repo import schedule_repo
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Literal

StatsFilter = Literal["mingguan", "bulanan", "tahunan"]
JAKARTA_TIMEZONE = timezone(timedelta(hours=7))

class AdminService:
    def _build_periods(self, stats_filter: StatsFilter):
        now = datetime.now(JAKARTA_TIMEZONE)

        if stats_filter == "mingguan":
            today_start = datetime(now.year, now.month, now.day, tzinfo=JAKARTA_TIMEZONE)
            return [
                {
                    "label": (today_start - timedelta(days=days_back)).strftime("%Y-%m-%d"),
                    "start": today_start - timedelta(days=days_back),
                    "end": today_start - timedelta(days=days_back - 1),
                }
                for days_back in range(6, -1, -1)
            ]

        if stats_filter == "bulanan":
            periods = []
            for month in range(1, 13):
                start = datetime(now.year, month, 1, tzinfo=JAKARTA_TIMEZONE)
                if month == 12:
                    end = datetime(now.year + 1, 1, 1, tzinfo=JAKARTA_TIMEZONE)
                else:
                    end = datetime(now.year, month + 1, 1, tzinfo=JAKARTA_TIMEZONE)
                periods.append({
                    "label": start.strftime("%Y-%m"),
                    "start": start,
                    "end": end,
                })
            return periods

        return [
            {
                "label": str(year),
                "start": datetime(year, 1, 1, tzinfo=JAKARTA_TIMEZONE),
                "end": datetime(year + 1, 1, 1, tzinfo=JAKARTA_TIMEZONE),
            }
            for year in range(now.year - 2, now.year + 1)
        ]

    async def get_stats(self, stats_filter: StatsFilter) -> Dict[str, Any]:
        periods = self._build_periods(stats_filter)
        start_date = periods[0]["start"]
        end_date = periods[-1]["end"]

        available_cars = await car_repo.count_by_status("Tersedia", start_date, end_date)
        sold_cars = await car_repo.count_by_status("Terjual", start_date, end_date)
        
        pending_schedules = await schedule_repo.count_by_status("pending", start_date, end_date)
        confirmed_schedules = await schedule_repo.count_by_status("confirmed", start_date, end_date)
        cancelled_schedules = await schedule_repo.count_by_status("cancelled", start_date, end_date)
        completed_schedules = await schedule_repo.count_by_status("completed", start_date, end_date)

        period_stats = []
        for period in periods:
            period_stats.append({
                "label": period["label"],
                "start_date": period["start"].isoformat(),
                "end_date": period["end"].isoformat(),
                "inventory": {
                    "available": await car_repo.count_by_status("Tersedia", period["start"], period["end"]),
                    "sold": await car_repo.count_by_status("Terjual", period["start"], period["end"])
                },
                "appointments": {
                    "pending": await schedule_repo.count_by_status("pending", period["start"], period["end"]),
                    "confirmed": await schedule_repo.count_by_status("confirmed", period["start"], period["end"]),
                    "cancelled": await schedule_repo.count_by_status("cancelled", period["start"], period["end"]),
                    "completed": await schedule_repo.count_by_status("completed", period["start"], period["end"])
                }
            })
        
        return {
            "filter": stats_filter,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "inventory": {
                "available": available_cars,
                "sold": sold_cars
            },
            "appointments": {
                "pending": pending_schedules,
                "confirmed": confirmed_schedules,
                "cancelled": cancelled_schedules,
                "completed": completed_schedules
            },
            "periods": period_stats
        }

admin_service = AdminService()
