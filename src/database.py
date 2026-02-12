from motor.motor_asyncio import AsyncIOMotorClient
from .config import settings

class Database:
    client: AsyncIOMotorClient = None
    db = None

    @classmethod
    async def connect(cls):
        """Connect to MongoDB."""
        if cls.client is None:
            cls.client = AsyncIOMotorClient(settings.MONGO_URI)
            cls.db = cls.client[settings.DB_NAME]
            print(f"✅ Connected to MongoDB: {settings.DB_NAME}")

    @classmethod
    async def close(cls):
        """Close MongoDB connection."""
        if cls.client:
            cls.client.close()
            cls.client = None
            print("❌ Closed MongoDB connection")

    @classmethod
    def get_collection(cls, name: str):
        """Get a collection."""
        return cls.db[name]

db = Database()
