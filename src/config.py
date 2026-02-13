import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load .env file
load_dotenv()

class Settings(BaseSettings):
    # API Keys
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    MONGO_URI: str = os.getenv("MONGO_URI", os.getenv("MONGODB_URI", "mongodb://localhost:27017"))
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
    HF_TOKEN: str = os.getenv("HF_TOKEN", "")

    # Service URLs
    ZAP_URL: str = os.getenv("ZAP_URL", "http://localhost:8080")
    ZAP_API_KEY: str = os.getenv("ZAP_API_KEY", "")

    # Paths & Models
    # Paths & Models
    DETECTION_MODEL_PATH: str = os.getenv("DETECTION_MODEL_PATH", "./redeye-detection-model")
    REPAIR_MODEL_PATH: str = os.getenv("REPAIR_MODEL_PATH", "./redeye-repair-model")
    REPAIR_BASE_MODEL: str = "t5-small"
    
    # DB Settings
    DB_NAME: str = "redeye"
    SCAN_COLLECTION: str = "scans"
    VULN_COLLECTION: str = "vulnerabilities"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
