import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = "redeye"

class Database:
    client: AsyncIOMotorClient = None
    db = None

    @classmethod
    async def connect(cls):
        """Connect to MongoDB."""
        if cls.client is None:
            cls.client = AsyncIOMotorClient(MONGO_URI)
            cls.db = cls.client[DB_NAME]
            print(f"✅ Connected to MongoDB: {DB_NAME}")

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
