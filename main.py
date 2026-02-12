import os
import time
from typing import List, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from contextlib import asynccontextmanager
from src.config import settings
from src.database import db
from src.rag_engine import rag_service
from src.expert_model import expert_model
from src.agent import agent_executor

# 1. Load Config (Handled by settings)
ZAP_URL = settings.ZAP_URL

# 2. Lifecycle Manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await db.connect()
    await rag_service.initialize()
    # expert_model.load_model() # Optional: Preload model on startup
    yield
    # Shutdown
    await db.close()

app = FastAPI(title="RedEye: AI Security Agent", version="2.0.0", lifespan=lifespan)

# --- CORS Configuration ---
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (Frontend, n8n, etc.)
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods (POST, GET, OPTIONS, etc.)
    allow_headers=["*"],
)

# --- Pydantic Models ---
import uuid

# --- Pydantic Models ---
class ScanRequest(BaseModel):
    target_url: str

class ScanResponse(BaseModel):
    scan_id: str
    status: str
    target: str
    agent_response: Optional[str] = None

# --- Background Task ---
async def background_scan_task(scan_id: str, target_url: str):
    """
    Background worker to run the heavy AI scan.
    """
    try:
        print(f"🕵️‍♂️ [Worker] Starting scan for {scan_id} ({target_url})")
        
        # 1. Run the Agent
        result = await agent_executor.ainvoke({
            "input": f"Please perform a full security scan on {target_url}. If you find vulnerabilities, verify them with your tools and suggest fixes based on past solutions."
        })
        agent_output = result["output"]

        # 2. Update DB as Completed
        await db.update_scan(scan_id, "completed", agent_output)
        print(f"✅ [Worker] Scan completed for {scan_id}")

    except Exception as e:
        print(f"❌ [Worker] Scan failed for {scan_id}: {e}")
        await db.update_scan(scan_id, "failed", {"error": str(e)})

# --- Endpoints ---
@app.get("/")
def health_check():
    return {"status": "ok", "infra": "Railway Ready", "zap_url": ZAP_URL}

@app.post("/scan", response_model=ScanResponse)
async def start_scan(request: ScanRequest, background_tasks: BackgroundTasks):
    """
    Starts an asynchronous scan. Returns a scan_id immediately.
    """
    scan_id = str(uuid.uuid4())
    
    # 1. Create Initial Record
    await db.create_scan(scan_id, request.target_url)

    # 2. Add to Background Queue
    background_tasks.add_task(background_scan_task, scan_id, request.target_url)

    return {
        "scan_id": scan_id,
        "status": "pending",
        "target": request.target_url
    }

@app.get("/scan/{scan_id}", response_model=ScanResponse)
async def get_scan_status(scan_id: str):
    """
    Poll this endpoint to check scan status.
    """
    scan = await db.get_scan(scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    return {
        "scan_id": scan["scan_id"],
        "status": scan["status"],
        "target": scan["target"],
        "agent_response": scan["agent_response"] if isinstance(scan["agent_response"], str) else str(scan.get("agent_response", ""))
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)