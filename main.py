
import os
import asyncio
import time
from typing import List, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from zapv2 import ZAPv2
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from src.database import db
from src.rag_engine import rag_engine

# 1. 환경 설정 로드 (로컬 .env 또는 Railway Variables)
load_dotenv()

# Railway 환경과 로컬 개발 환경을 동시에 지원하는 설정
ZAP_URL = os.getenv("ZAP_URL", "http://zap-service.railway.internal:8080")
ZAP_API_KEY = os.getenv("ZAP_API_KEY", "redeye1234")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# 2. FastAPI 앱 초기화 (Lifespan으로 DB 연결)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    db.connect()
    rag_engine.initialize()
    yield
    # Shutdown
    await db.close()

app = FastAPI(title="RedEye: AI Security Scanner", version="2.0.0", lifespan=lifespan)

# 3. ZAP 클라이언트 연결 설정
# Railway 내부 통신일 때는 프록시 설정이 필요 없을 수 있으나, 명시적으로 지정
zap = ZAPv2(apikey=ZAP_API_KEY, proxies={'http': ZAP_URL, 'https': ZAP_URL})

# 4. AI 모델 설정 (GPT-4o or 3.5-turbo)
llm = ChatOpenAI(
    model="gpt-4o-mini", 
    temperature=0.3, # 가성비 모델 사용 (gpt-4o-mini)
    openai_api_key=OPENAI_API_KEY
)

# --- Pydantic Models ---
class ScanRequest(BaseModel):
    target_url: str

class ScanResult(BaseModel):
    target: str
    alerts_count: int
    ai_analysis: str

# --- System Prompt ---
SYSTEM_PROMPT = """
# Role Definition (역할 정의)
당신은 "RedEye" 프로젝트의 **수석 보안 엔지니어**이자 **CTO**입니다.
당신은 현재 **Railway 클라우드 환경**에 배포된 **FastAPI 서버** 내부에서 동작하고 있습니다.

# Infrastructure Context (중요: 인프라 환경 인지)
우리의 서비스 아키텍처는 **Railway** 위에서 두 개의 독립된 마이크로서비스로 구동됩니다.
1. **Backend (This Service)**: FastAPI + LangChain + Docker (현재 당신이 실행 중인 곳).
2. **Scanner Engine (OWASP ZAP)**: 별도의 Docker 컨테이너로 실행됨.
   - **통신 방식**: Railway Private Networking을 사용합니다.
   - **주소**: `localhost`가 아닙니다. 환경 변수 `ZAP_URL` (예: `http://zap-service.railway.internal:8080`)을 통해 접속합니다.
   - **인증**: `ZAP_API_KEY` 환경 변수를 사용합니다.

# Your Goal (목표)
OWASP ZAP 스캐너가 탐지한 취약점 로그를 분석하여, 개발자가 즉시 적용 가능한 **수정 코드(Patch)**와 **비즈니스 인사이트**를 제공하십시오.

# Persona & Tone (페르소나)
- **전문적이고 냉철함**: 스캐너의 결과를 맹신하지 말고 검증하십시오.
- **인프라 인식(Awareness)**: 문제 해결책 제안 시, 우리가 Docker/Railway 환경임을 고려하십시오. (예: "파일 시스템에 직접 로그를 남기지 말고 STDOUT을 쓰세요.")
- **공동 창업자 마인드**: 치명적인 보안 위협은 강력하게 경고하고, 오탐(False Positive)은 과감하게 무시하라고 조언하십시오.

# Output Format (Markdown)

## 🚨 [위험도: High/Medium/Low] <취약점 타이틀>

**요약 (Executive Summary):**
(개발자가 한눈에 알 수 있는 1문장 요약)

**비즈니스 임팩트 (Why it matters):**
(구체적인 해킹 시나리오 및 피해 예상)

**기술적 분석 (Technical Analysis):**
(로그 데이터 기반의 기술적 원인 분석)

# ❌ 취약한 코드
...
# ✅ 보안 패치 코드 (FastAPI/Python 권장)
...
"""

# --- Helper Functions ---
async def run_zap_scan(target_url: str):
    print(f"🚀 [ZAP] Scanning target: {target_url} via {ZAP_URL}")
    
    # 1. Spidering (크롤링)
    scan_id = zap.spider.scan(target_url)
    while int(zap.spider.status(scan_id)) < 100:
        await asyncio.sleep(2)
    print("✅ [ZAP] Spidering complete.")

    # 2. Active Scan (실제 공격 - 필요시 주석 해제, 시간이 오래 걸림)
    # scan_id = zap.ascan.scan(target_url)
    # while int(zap.ascan.status(scan_id)) < 100:
    #    await asyncio.sleep(5)
    
    # 3. 결과 수집
    alerts = zap.core.alerts(baseurl=target_url)
    return alerts

async def analyze_with_ai(alerts: List[dict]) -> str:
    if not alerts:
        return "보안 취약점이 발견되지 않았습니다."

    critical_alerts = [a for a in alerts if a.get('risk') in ['High', 'Medium']]
    
    if not critical_alerts:
        return "치명적인(High/Medium) 취약점은 발견되지 않았습니다."

    # --- RAG: 과거 유사 사례 검색 ---
    rag_context = ""
    try:
        # 가장 위험한 취약점 하나를 골라서 유사 사례 검색 (데모용)
        # 실제로는 모든 Alert에 대해 검색하거나 요약해서 검색해야 함
        query_alert = critical_alerts[0]
        query_text = f"{query_alert.get('name')} {query_alert.get('description')}"
        
        similar_docs = await rag_engine.search_similar_issues(query_text)
        if similar_docs:
            rag_context = "\n\n## 📚 Past Similar Incidents (RAG Context):\n"
            for doc in similar_docs:
                rag_context += f"- {doc.page_content[:200]}...\n"
    except Exception as e:
        print(f"RAG Error: {e}")

    # AI에게 보낼 메시지 구성
    user_message = f"""
    Here is the raw ZAP Alert Data (JSON):
    {str(critical_alerts)[:10000]}

    {rag_context}
    
    If 'Past Similar Incidents' are provided, please reference them in your analysis to suggest consistent solutions.
    """

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_message)
    ]
    
    response = await llm.ainvoke(messages)
    return response.content

# --- Endpoints ---
@app.get("/")
def health_check():
    return {"status": "ok", "infra": "Railway Ready", "zap_url": ZAP_URL}

@app.post("/scan", response_model=ScanResult)
async def start_scan(request: ScanRequest):
    try:
        # 1. ZAP 스캔 수행
        raw_alerts = await run_zap_scan(request.target_url)
        
        # 2. AI 분석 수행 (RAG 포함)
        analysis_report = await analyze_with_ai(raw_alerts)
        
        # 3. 데이터 저장 (RAG 학습)
        # 중요 취약점만 벡터 DB에 저장
        critical_alerts = [a for a in raw_alerts if a.get('risk') in ['High', 'Medium']]
        if critical_alerts:
            await rag_engine.ingest_alerts(critical_alerts)
            
        # 4. 전체 결과 저장 (로그용)
        if db.get_db() is not None:
             await db.get_db()["scan_history"].insert_one({
                 "target": request.target_url,
                 "alerts_count": len(raw_alerts),
                 "analysis": analysis_report,
                 "timestamp": time.time() # time import needed? No, use datetime or skip for MVP
             })
        
        return {
            "target": request.target_url,
            "alerts_count": len(raw_alerts),
            "ai_analysis": analysis_report
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)