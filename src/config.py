import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import Field

# Load .env file
load_dotenv()

class Settings(BaseSettings):
    # API Keys
    OPENAI_API_KEY: str = ""
    GITHUB_TOKEN: str = ""
    HF_TOKEN: str = ""

    # Database
    MONGO_URI: str = Field(default="mongodb://localhost:27017")
    MONGODB_URI: str = Field(default="mongodb://localhost:27017")  # Fallback

    # Service URLs
    ZAP_URL: str = "http://localhost:8080"
    ZAP_API_KEY: str = ""

    # Paths & Models
    DETECTION_MODEL_PATH: str = "kimdonghwanAIengineer/redeye-detection-quantized"
    REPAIR_MODEL_PATH: str = "kimdonghwanAIengineer/redeye-repair-quantized"
    REPAIR_BASE_MODEL: str = "t5-small"
    
    # DB Settings
    DB_NAME: str = "redeye"
    SCAN_COLLECTION: str = "scans"
    VULN_COLLECTION: str = "vulnerabilities"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

# Fallback for MONGO_URI (use MONGODB_URI if MONGO_URI is not set)
if settings.MONGO_URI == "mongodb://localhost:27017" and settings.MONGODB_URI != "mongodb://localhost:27017":
    settings.MONGO_URI = settings.MONGODB_URI

