from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.core.config import settings

class Database:
    client: AsyncIOMotorClient = None

db = Database()

async def init_db():
    # Import models here to avoid circular imports
    from app.models.user import User
    from app.models.car import Car
    from app.models.schedule import Schedule
    from app.models.chat import ChatHistory

    db.client = AsyncIOMotorClient(settings.MONGODB_URL)
    database = db.client[settings.MONGODB_DB_NAME]
    
    await init_beanie(
        database=database,
        document_models=[
            User,
            Car,
            Schedule,
            ChatHistory
        ]
    )

async def close_db():
    if db.client:
        db.client.close()
