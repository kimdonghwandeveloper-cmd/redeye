from motor.motor_asyncio import AsyncIOMotorClient
from .config import settings

class Database:
    client: AsyncIOMotorClient = None
    db = None

    @classmethod
    async def connect(cls):
        """Connect to MongoDB."""
        import certifi
        if cls.client is None:
            cls.client = AsyncIOMotorClient(
                settings.MONGO_URI,
                tlsCAFile=certifi.where()
            )
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
    async def get_collection(cls, name: str):
        """Get a collection."""
        return cls.db[name]

    @classmethod
    async def create_scan(cls, scan_id: str, target_url: str):
        """Create a new scan record."""
        await cls.db["scans"].insert_one({
            "scan_id": scan_id,
            "target": target_url,
            "status": "pending",
            "agent_response": None,
            "created_at": None  # Will be set by time.time() in main
        })

    @classmethod
    async def update_scan(cls, scan_id: str, status: str, result: dict = None):
        """Update scan status and result."""
        update_data = {"status": status}
        if result:
            update_data["agent_response"] = result
        
        await cls.db["scans"].update_one(
            {"scan_id": scan_id},
            {"$set": update_data}
        )

    @classmethod
    async def get_scan(cls, scan_id: str):
        """Get scan by ID."""
        return await cls.db["scans"].find_one({"scan_id": scan_id}, {"_id": 0})

db = Database()
