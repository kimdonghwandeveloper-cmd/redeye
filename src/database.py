import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI") or os.getenv("MONGODB_URI") or os.getenv("MONGO_URL")
DB_NAME = "RedEye"

class Database:
    client: AsyncIOMotorClient = None
    
    def connect(self):
        if not MONGO_URI:
            print("⚠️ MONGO_URI not found in env. Database features will be disabled.")
            return
        
        self.client = AsyncIOMotorClient(MONGO_URI)
        print("✅ Connected to MongoDB via Motor")

    def get_db(self):
        return self.client[DB_NAME] if self.client else None

    async def close(self):
        if self.client:
            self.client.close()
            print("🛑 Closed MongoDB connection")

db = Database()
