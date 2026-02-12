import asyncio
import os
from unittest.mock import MagicMock, AsyncMock

# Mock DB and Agent
mock_db = MagicMock()
mock_db.db = True
mock_db.update_scan = AsyncMock()

mock_agent_executor = MagicMock()
mock_agent_executor.ainvoke = AsyncMock(return_value={"output": "Mock Agent Output"})

# Mock Config
class MockSettings:
    MONGO_URI = "mongodb://localhost:27017"
    DB_NAME = "redeye"
    ZAP_URL = "http://localhost:8080"

# Monkey patch modules
import sys
sys.modules["src.database"] = MagicMock()
sys.modules["src.database"].db = mock_db
sys.modules["src.config"] = MagicMock()
sys.modules["src.config"].settings = MockSettings()
sys.modules["src.agent"] = MagicMock()
sys.modules["src.agent"].agent_executor = mock_agent_executor

# Import main (after mocking)
# We need to extract the background_scan_task function or recreate it to test logic
# Since we can't easily import from main without triggers, let's copy the logic to test it.

async def background_scan_task_sim(scan_id: str, target_url: str, language: str = "en"):
    print(f"🕵️‍♂️ [Worker] Starting scan for {scan_id} ({target_url}) in {language}")
    
    try:
        # 1. Run the Agent
        lang_instruction = "IMPORTANT: Please respond in Korean (한국어)." if language == "ko" else "IMPORTANT: Please respond in English."
        
        # Simulate invoke
        print(f"Invoking agent with language: {language}")
        if language not in ["en", "ko"]:
             raise ValueError("Invalid language")

        result = await mock_agent_executor.ainvoke({
            "input": f"Please perform a full security scan on {target_url}. ...\n\n{lang_instruction}"
        })
        agent_output = result["output"]

        # 2. Update DB
        if mock_db.db is not None:
             await mock_db.update_scan(scan_id, "completed", agent_output)
             print(f"✅ [Worker] Scan completed for {scan_id}")
        else:
             print(f"❌ [Worker] DB is not connected.")

    except Exception as e:
        print(f"❌ [Worker] Scan failed for {scan_id}: {e}")
        await mock_db.update_scan(scan_id, "failed", {"error": str(e)})

async def main():
    print("--- Test 1: English Scan ---")
    await background_scan_task_sim("test-id-1", "http://example.com", "en")
    
    print("\n--- Test 2: Korean Scan ---")
    await background_scan_task_sim("test-id-2", "http://example.com", "ko")

    print("\n--- Test 3: Invalid Language (Should pass but default to English logic if not handled, but here logic handles en/ko) ---")
    await background_scan_task_sim("test-id-3", "http://example.com", "fr")

if __name__ == "__main__":
    asyncio.run(main())
