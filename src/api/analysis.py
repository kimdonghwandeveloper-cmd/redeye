from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import Optional, List, Any
from src.expert_model import expert_model
from src.repo_scanner import repo_scanner
from src.github_diff_scanner import github_diff_scanner
import logging

router = APIRouter(prefix="/analyze", tags=["Analysis"])
logger = logging.getLogger(__name__)

# --- Request Models ---
class CodeAnalysisRequest(BaseModel):
    code: str
    language: Optional[str] = "python"
    filename: Optional[str] = "snippet"

class CodeRepairRequest(BaseModel):
    code: str
    vulnerability_type: Optional[str] = "Generic Vulnerability"

class PRAnalysisRequest(BaseModel):
    owner: str
    repo: str
    pr_number: int
    max_files: Optional[int] = 50

# --- Endpoints ---

@router.post("/code")
async def analyze_code(request: CodeAnalysisRequest):
    """
    Analyzes a code snippet for vulnerabilities using a Hybrid approach:
    1. Static Analysis (Regex Patterns via RepoScanner)
    2. AI Analysis (CodeBERT via ExpertModel)
    
    Returns a combined report.
    """
    try:
        results = {
            "sast_alerts": [],
            "ai_verification": {},
            "is_vulnerable": False
        }

        # 1. SAST Scan (Fast Filter)
        # We strip the code to ensure clean input
        sast_alerts = repo_scanner.scan_content(request.code, filename=request.filename)
        results["sast_alerts"] = sast_alerts

        # 2. AI Verification (Deep Scan)
        # We verify the whole snippet. In a real-world scenario, we might only verify 
        # the specific lines flagged by SAST, but here we check the context.
        ai_result = expert_model.verify(request.code)
        results["ai_verification"] = ai_result

        # 3. Final Verdict Logic
        # - If AI says VULNERABLE with high confidence (> 0.8), it's vulnerable.
        # - If SAST finds High Risk patterns AND AI is unsure, mark as potential.
        if ai_result.get("label") == "VULNERABLE" and ai_result.get("confidence", 0) > 0.5:
             results["is_vulnerable"] = True
        elif len(sast_alerts) > 0 and ai_result.get("label") == "VULNERABLE":
             # AI confirms SAST
             results["is_vulnerable"] = True
        
        return results

    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/repair")
async def repair_code(request: CodeRepairRequest):
    """
    Generates a fix for the provided vulnerable code using the AI Repair Model (T5).
    """
    try:
        # We can optionally prepend the vulnerability type to the prompt
        # input_text = f"fix {request.vulnerability_type}: {request.code}"
        # But the model is trained on "fix vulnerability: ..." mostly.
        
        fix_result = expert_model.repair(request.code)
        
        if "error" in fix_result and fix_result["error"]:
             raise HTTPException(status_code=500, detail=fix_result["error"])
             
        return {
            "original_code": request.code,
            "fixed_code": fix_result["fixed_code"],
            "vulnerability_type": request.vulnerability_type
        }

    except Exception as e:
        logger.error(f"Repair failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/pr")
async def analyze_pr(request: PRAnalysisRequest):
    """
    GitHub PR의 변경된 코드만 스캔 (GitHub Diff API 사용)
    
    CodeRabbit 방식:
    - Git Clone 대신 변경된 diff만 가져오기
    - 네트워크 효율: 수백 MB → 수 KB
    - 속도: 수 분 → 몇 초
    
    Initial Commit 대응:
    - 파일 수가 max_files를 초과하면 중요한 파일만 필터링
    - 보안 관련 키워드 우선순위 (auth, password, secret, etc.)
    """
    try:
        result = await github_diff_scanner.scan_pr_diff(
            owner=request.owner,
            repo=request.repo,
            pr_number=request.pr_number,
            max_files=request.max_files
        )
        
        return result
        
    except Exception as e:
        logger.error(f"PR scan failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
