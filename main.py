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

# --- Pydantic Models ---
class ScanRequest(BaseModel):
    target_url: str

class ScanResult(BaseModel):
    target: str
    status: str
    agent_response: str

# --- Endpoints ---
@app.get("/")
def health_check():
    return {"status": "ok", "infra": "Railway Ready", "zap_url": ZAP_URL}

@app.post("/scan", response_model=ScanResult)
async def start_scan(request: ScanRequest):
    """
    Triggers the AI Security Agent to scan, analyze, and report.
    """
    try:
        print(f"🕵️‍♂️ [Agent] Received scan request for: {request.target_url}")
        
        # Invoke the ReAct Agent
        # The agent will: Scan (ZAP) -> Verify (Expert Model) -> Search (RAG) -> Report
        result = await agent_executor.ainvoke({
            "input": f"Please perform a full security scan on {request.target_url}. If you find vulnerabilities, verify them with your tools and suggest fixes based on past solutions."
        })
        
        agent_output = result["output"]

        # Store in DB (Log)
        try:
            if db.db is not None:
                 await db.db["scan_history"].insert_one({
                     "target": request.target_url,
                     "agent_response": agent_output,
                     "timestamp": time.time()
                 })
        except Exception as e:
            print(f"⚠️ Failed to log scan history to DB: {e}")
        
        return {
            "target": request.target_url,
            "status": "Completed",
            "agent_response": agent_output
        }
        
    except Exception as e:
        print(f"❌ Error during scan: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)