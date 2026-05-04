import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.core.config import settings
from app.models.user import User
from app.models.car import Car
from app.models.schedule import Schedule
from app.core.security import get_password_hash

async def seed():
    # Gunakan localhost untuk koneksi dari script luar docker
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    database = client[settings.MONGODB_DB_NAME]
    
    await init_beanie(
        database=database,
        document_models=[User, Car, Schedule]
    )
    
    print("Menghapus data lama...")
    await User.delete_all()
    await Car.delete_all()
    await Schedule.delete_all()

    print("Membuat data admin & user...")
    admin = User(
        username="admin",
        email="admin@showroom.com",
        phone="081234567890",
        hashed_password=get_password_hash("admin123"),
        role="admin"
    )
    await admin.insert()

    user = User(
        username="johndoe",
        email="john@example.com",
        phone="089876543210",
        hashed_password=get_password_hash("password123"),
        role="customer"
    )
    await user.insert()

    print("Membuat data mobil...")
    gdrive_images = [
        "https://lh3.googleusercontent.com/d/1ly-yWT7jQuD2GxRlg6DIiCf0GfmipUmv",
        "https://lh3.googleusercontent.com/d/1oDaGpkS5JZInRPzMeu-juqYjU_pfzzSD",
        "https://lh3.googleusercontent.com/d/1PJiiHy-uhMCjMNrCGCV1Wm3hWpJL5SLk"
    ]

    cars = [
        Car(
            brand="Toyota Avanza",
            type="MPV",
            year=2022,
            price=250000000,
            transmission="Automatic",
            mileage=15000,
            fuel="Bensin",
            color="Hitam",
            description="Mobil keluarga idaman, irit dan nyaman.",
            status="Tersedia",
            features=["AC", "Airbag", "Bluetooth"],
            images=[gdrive_images[0]]
        ),
        Car(
            brand="Honda Civic",
            type="Sedan",
            year=2023,
            price=550000000,
            transmission="Automatic",
            mileage=5000,
            fuel="Bensin",
            color="Putih",
            description="Desain sporty dan performa luar biasa.",
            status="Tersedia",
            features=["Sunroof", "Leather Seats", "Cruise Control"],
            images=[gdrive_images[1]]
        ),
        Car(
            brand="Mitsubishi Pajero Sport",
            type="SUV",
            year=2021,
            price=480000000,
            transmission="Automatic",
            mileage=35000,
            fuel="Diesel",
            color="Silver",
            description="Tangguh di segala medan.",
            status="Tersedia",
            features=["4WD", "Rear Camera", "ABS"],
            images=[gdrive_images[2]]
        ),
        Car(
            brand="Suzuki Ertiga",
            type="MPV",
            year=2020,
            price=190000000,
            transmission="Manual",
            mileage=45000,
            fuel="Bensin",
            color="Abu-abu",
            description="MPV ekonomis dan handal.",
            status="Terjual",
            features=["AC", "Power Steering"],
            images=[gdrive_images[0]]
        ),
        Car(
            brand="Hyundai Ioniq 5",
            type="Hatchback",
            year=2024,
            price=800000000,
            transmission="Automatic",
            mileage=1000,
            fuel="Listrik",
            color="Gravity Gold Matte",
            description="Mobil listrik masa depan dengan fitur premium.",
            status="Tersedia",
            features=["EV", "Panoramic Sunroof", "Smart Sense"],
            images=[gdrive_images[1]]
        )
    ]
    
    for car in cars:
        await car.insert()
        
    print("Berhasil memasukkan data dummy!")
    client.close()

if __name__ == "__main__":
    asyncio.run(seed())
