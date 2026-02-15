from motor.motor_asyncio import AsyncIOMotorClient
from .config import settings
from datetime import datetime, timedelta
import uuid

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
                tls=True,
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

    # --- Scan Management ---
    @classmethod
    async def create_scan(cls, scan_id: str, target_url: str):
        """Create a new scan record."""
        await cls.db["scans"].insert_one({
            "scan_id": scan_id,
            "target": target_url,
            "status": "pending",
            "agent_response": None,
            "created_at": None
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

    # --- GitHub Session Management ---
    @classmethod
    async def save_user_session(cls, github_user: dict, access_token: str) -> str:
        """
        GitHub OAuth 로그인 후 세션을 MongoDB에 저장.
        Returns: session_id (UUID)
        """
        session_id = str(uuid.uuid4())
        
        session_data = {
            "session_id": session_id,
            "github_id": github_user.get("id"),
            "github_user": github_user.get("login"),
            "avatar_url": github_user.get("avatar_url"),
            "access_token": access_token,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(days=30)
        }
        
        # 기존 세션이 있으면 업데이트, 없으면 생성
        await cls.db["sessions"].update_one(
            {"github_id": github_user.get("id")},
            {"$set": session_data},
            upsert=True
        )
        
        print(f"✅ Session saved for {github_user.get('login')} ({session_id[:8]}...)")
        return session_id

    @classmethod
    async def get_user_session(cls, session_id: str) -> dict:
        """session_id로 유저 세션 조회."""
        session = await cls.db["sessions"].find_one(
            {"session_id": session_id},
            {"_id": 0}
        )
        
        if not session:
            return None
        
        # 만료 확인
        if session.get("expires_at") and session["expires_at"] < datetime.utcnow():
            await cls.delete_user_session(session_id)
            return None
        
        return session

    @classmethod
    async def delete_user_session(cls, session_id: str):
        """세션 삭제 (로그아웃)."""
        await cls.db["sessions"].delete_one({"session_id": session_id})
        print(f"🗑️ Session deleted: {session_id[:8]}...")

db = Database()
