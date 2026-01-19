
import os
import time
from typing import List, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from zapv2 import ZAPv2
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv

# 1. 환경 설정 로드 (로컬 .env 또는 Railway Variables)
load_dotenv()

# Railway 환경과 로컬 개발 환경을 동시에 지원하는 설정
ZAP_URL = os.getenv("ZAP_URL", "http://localhost:8080")
ZAP_API_KEY = os.getenv("ZAP_API_KEY", "redeye1234")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# 2. FastAPI 앱 초기화
app = FastAPI(title="RedEye: AI Security Scanner", version="1.0.0")

# 3. ZAP 클라이언트 연결 설정
# Railway 내부 통신일 때는 프록시 설정이 필요 없을 수 있으나, 명시적으로 지정
zap = ZAPv2(apikey=ZAP_API_KEY, proxies={'http': ZAP_URL, 'https': ZAP_URL})

# 4. AI 모델 설정 (GPT-4o or 3.5-turbo)
llm = ChatOpenAI(
    model="gpt-4o", 
    temperature=0.3, # 보안 분석은 창의성보다 정확성이 중요
    openai_api_key=OPENAI_API_KEY
)

# --- Pydantic Models ---
class ScanRequest(BaseModel):
    target_url: str

class ScanResult(BaseModel):
    target: str
    alerts_count: int
    ai_analysis: str

# --- System Prompt (위에서 정의한 내용) ---
SYSTEM_PROMPT = """
# Role Definition
당신은 "RedEye" 프로젝트의 수석 보안 엔지니어이자 CTO입니다.
당신은 현재 Railway 클라우드 환경에 배포된 FastAPI 서버 내부에서 동작하고 있습니다.

# Infrastructure Context
- Backend: FastAPI + Docker
- Scanner: OWASP ZAP (Separate Container via Private Networking)
- Address: ZAP_URL env var used.

(나머지 프롬프트 내용은 위와 동일하다고 가정하고 생략 - 실제로는 꽉 채워야 함)
...
OWASP ZAP 로그를 분석하고 개발자에게 수정 코드를 제안하십시오.
"""

# --- Helper Functions ---
def run_zap_scan(target_url: str):
    print(f"🚀 [ZAP] Scanning target: {target_url} via {ZAP_URL}")
    
    # 1. Spidering (크롤링)
    scan_id = zap.spider.scan(target_url)
    while int(zap.spider.status(scan_id)) < 100:
        time.sleep(2)
    print("✅ [ZAP] Spidering complete.")

    # 2. Active Scan (실제 공격 - 필요시 주석 해제, 시간이 오래 걸림)
    # scan_id = zap.ascan.scan(target_url)
    # while int(zap.ascan.status(scan_id)) < 100:
    #    time.sleep(5)
    
    # 3. 결과 수집
    alerts = zap.core.alerts(baseurl=target_url)
    return alerts

def analyze_with_ai(alerts: List[dict]) -> str:
    if not alerts:
        return "보안 취약점이 발견되지 않았습니다. (시스템이 매우 안전하거나, 스캔이 제대로 동작하지 않았습니다.)"

    # High/Medium 위험도만 필터링해서 토큰 절약
    critical_alerts = [a for a in alerts if a.get('risk') in ['High', 'Medium']]
    
    if not critical_alerts:
        return "치명적인(High/Medium) 취약점은 발견되지 않았습니다. Low 레벨 경고만 존재합니다."

    # AI에게 보낼 메시지 구성
    # JSON 전체를 문자열로 변환하여 전송
    user_message = f"Here is the raw ZAP Alert Data (JSON):\n{str(critical_alerts)[:15000]}" 
    # 토큰 제한 고려하여 15000자 정도만 (필요시 조절)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_message)
    ]
    
    response = llm.invoke(messages)
    return response.content

# --- Endpoints ---
@app.get("/")
def health_check():
    return {"status": "ok", "infra": "Railway Ready", "zap_url": ZAP_URL}

@app.post("/scan", response_model=ScanResult)
def start_scan(request: ScanRequest):
    """
    URL을 받아서 ZAP 스캔을 돌리고 -> AI 분석 결과를 반환
    (오래 걸리므로 실제 프로덕션에서는 비동기 큐(Celery/Redis) 권장)
    """
    try:
        # 1. ZAP 스캔 수행
        raw_alerts = run_zap_scan(request.target_url)
        
        # 2. AI 분석 수행
        analysis_report = analyze_with_ai(raw_alerts)
        
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