import asyncio
import json
import os
import sys
from datetime import datetime, timezone, timedelta, date
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

# Tambahkan root directory ke sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.car import Car
from app.models.user import User
from app.models.location import Location
from app.models.available_slot import AvailableSlot
from app.models.schedule import Schedule
from app.models.chat import ChatHistory
from app.core.config import settings

SEED_DIR = os.path.dirname(__file__)

def load_json(filename: str):
    path = os.path.join(SEED_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

# ─────────────────────────────────────────────
# 1. SEED USERS
# ─────────────────────────────────────────────
async def seed_users() -> list[User]:
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    users_data = load_json("users_data.json")
    seeded = []

    print("\n── Seeding Users ──")
    for data in users_data:
        existing = await User.find_one(User.username == data["username"])
        if existing:
            print(f"  SKIP  : {data['username']} (already exists)")
            seeded.append(existing)
            continue

        user = User(
            username=data["username"],
            email=data["email"],
            phone=data.get("phone", ""),
            hashed_password=pwd_context.hash(data["password"]),
            role=data.get("role", "customer")
        )
        await user.insert()
        seeded.append(user)
        print(f"  INSERT: {data['username']} ({data['role']})")

    return seeded

# ─────────────────────────────────────────────
# 2. SEED LOCATIONS
# ─────────────────────────────────────────────
async def seed_locations() -> list[Location]:
    locations_data = load_json("locations_data.json")
    seeded = []

    print("\n── Seeding Locations ──")
    for data in locations_data:
        existing = await Location.find_one(Location.location_name == data["location_name"])
        if existing:
            print(f"  SKIP  : {data['location_name']} (already exists)")
            seeded.append(existing)
            continue

        loc = Location(
            location_name=data["location_name"],
            address=data["address"],
            map_link=data["map_link"]
        )
        await loc.insert()
        seeded.append(loc)
        print(f"  INSERT: {data['location_name']}")

    return seeded

# ─────────────────────────────────────────────
# 3. SEED AVAILABLE SLOTS
# ─────────────────────────────────────────────
async def seed_available_slots(locations: list[Location]) -> list[AvailableSlot]:
    slots_data = load_json("available_slots_data.json")
    seeded = []
    today = date.today()

    print("\n── Seeding Available Slots ──")
    for data in slots_data:
        # Lewati key 'comment'
        if "comment" in data:
            continue

        loc_index = data["location_index"]
        if loc_index >= len(locations):
            print(f"  WARN  : location_index {loc_index} out of range, skipping")
            continue

        location = locations[loc_index]
        slot_date = today + timedelta(days=data["date_offset_days"])

        # Cek duplikasi berdasarkan location, date, dan time_start
        existing = await AvailableSlot.find_one(
            AvailableSlot.location_id == location.id,
            AvailableSlot.date == slot_date,
            AvailableSlot.time_start == data["time_start"]
        )
        if existing:
            print(f"  SKIP  : Slot {location.location_name} | {slot_date} {data['time_start']} (already exists)")
            seeded.append(existing)
            continue

        slot = AvailableSlot(
            location_id=location.id,
            date=slot_date,
            time_start=data["time_start"],
            time_end=data["time_end"],
            quota=data.get("quota", 1),
            booked_count=0
        )
        await slot.insert()
        seeded.append(slot)
        print(f"  INSERT: {location.location_name} | {slot_date} {data['time_start']}-{data['time_end']} (quota: {data['quota']})")

    return seeded

# ─────────────────────────────────────────────
# 4. SEED CARS
# ─────────────────────────────────────────────
async def seed_cars() -> list[Car]:
    cars_data = load_json("cars_data.json")
    seeded = []

    print("\n── Seeding Cars ──")
    for data in cars_data:
        existing = await Car.find_one(Car.model == data["type"], Car.year == data["year"], Car.price == data["price"])
        if existing:
            print(f"  SKIP  : {data['brand']} {data['type']} {data['year']} (already exists)")
            seeded.append(existing)
            continue

        car = Car(
            brand=data["brand"],
            model=data["type"],
            year=data["year"],
            price=data["price"],
            transmission=data["transmission"],
            mileage=data["mileage"],
            fuel=data["fuel"],
            color=data["color"],
            description=data["description"],
            status=data["status"],
            features=data["features"],
            images=data["images"]
        )
        await car.insert()
        seeded.append(car)
        print(f"  INSERT: {data['brand']} {data['type']} ({data['year']})")

    return seeded

# ─────────────────────────────────────────────
# 5. SEED SCHEDULES (sample bookings)
# ─────────────────────────────────────────────
async def seed_schedules(users: list[User], cars: list[Car], slots: list[AvailableSlot]):
    print("\n── Seeding Sample Schedules ──")
    
    # Ambil user customer saja
    customers = [u for u in users if u.role == "customer"]
    available_cars = [c for c in cars if c.status == "Tersedia"]
    available_slots = [s for s in slots if s.booked_count < s.quota]

    if not customers or not available_cars or not available_slots:
        print("  SKIP  : Tidak ada cukup data untuk membuat sample schedule")
        return

    # Buat maksimal 3 sample booking dengan slot yang berbeda-beda
    sample_bookings = [
        (customers[0], available_cars[0], available_slots[0], "Ingin test drive weekend ini"),
        (customers[1], available_cars[1], available_slots[1], "Tertarik untuk melihat kondisi langsung"),
        (customers[2], available_cars[2] if len(available_cars) > 2 else available_cars[0], 
         available_slots[2] if len(available_slots) > 2 else available_slots[0], 
         "Mau survey dulu sebelum beli"),
    ]

    for user, car, slot, notes in sample_bookings:
        # Cek apakah sudah ada booking dengan kombinasi yang sama
        existing = await Schedule.find_one(
            Schedule.user_id == user.id,
            Schedule.slot_id == slot.id
        )
        if existing:
            print(f"  SKIP  : Booking {user.username} -> {car.brand} {car.model} (already exists)")
            continue

        schedule = Schedule(
            user_id=user.id,
            car_id=car.id,
            slot_id=slot.id,
            notes=notes,
            status="pending"
        )
        await schedule.insert()

        # Update booked_count pada slot yang digunakan
        slot.booked_count += 1
        await slot.save()

        print(f"  INSERT: {user.username} -> {car.brand} {car.model} @ slot {slot.date} {slot.time_start}")

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
async def seed():
    print("=" * 50)
    print("  AUTOCATALOG DATABASE SEEDER")
    print("=" * 50)
    print(f"  Database: {settings.MONGODB_DB_NAME}")
    print(f"  URL     : {settings.MONGODB_URL}")

    client = AsyncIOMotorClient(settings.MONGODB_URL)
    await init_beanie(
        database=client[settings.MONGODB_DB_NAME],
        document_models=[Car, User, Location, AvailableSlot, Schedule, ChatHistory]
    )

    users     = await seed_users()
    locations = await seed_locations()
    cars      = await seed_cars()
    slots     = await seed_available_slots(locations)
    await seed_schedules(users, cars, slots)

    print("\n" + "=" * 50)
    print("  SEEDING COMPLETE!")
    print(f"  Users    : {len(users)}")
    print(f"  Locations: {len(locations)}")
    print(f"  Cars     : {len(cars)}")
    print(f"  Slots    : {len(slots)}")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(seed())
