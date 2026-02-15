import os
import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv
from src.database import db

load_dotenv()

router = APIRouter()

# Configuration
GITHUB_CLIENT_ID = os.getenv("CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("CLIENT_SECRET")
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8000") 
CALLBACK_URL = f"{APP_BASE_URL}/auth/github/callback"
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

class Repo(BaseModel):
    id: int
    name: str
    full_name: str
    html_url: str
    description: Optional[str] = None
    private: bool
    language: Optional[str] = None


@router.get("/auth/github/login")
async def login_with_github():
    """GitHub OAuth 로그인 페이지로 리다이렉트."""
    if not GITHUB_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Server misconfigured: Missing GITHUB_CLIENT_ID")
    
    scope = "read:user repo"
    github_auth_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={GITHUB_CLIENT_ID}"
        f"&redirect_uri={CALLBACK_URL}"
        f"&scope={scope}"
    )
    return RedirectResponse(url=github_auth_url)


@router.get("/auth/github/callback")
async def github_callback(code: str):
    """
    GitHub OAuth 콜백: 
    1. code → access_token 교환
    2. GitHub 유저 정보 가져오기
    3. MongoDB에 세션 저장
    4. session_id만 프런트엔드에 전달
    """
    if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Server misconfigured: Missing Credentials")

    async with httpx.AsyncClient() as client:
        # 1. code → access_token 교환
        token_response = await client.post(
            "https://github.com/login/oauth/access_token",
            json={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": CALLBACK_URL
            },
            headers={"Accept": "application/json"}
        )
        
        if token_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to retrieve access token")
        
        token_data = token_response.json()
        if "error" in token_data:
            raise HTTPException(status_code=400, detail=f"GitHub Error: {token_data.get('error_description')}")
        
        access_token = token_data.get("access_token")

        # 2. GitHub 유저 정보 가져오기
        user_response = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github.v3+json"
            }
        )
        
        if user_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch GitHub user info")
        
        github_user = user_response.json()

    # 3. MongoDB에 세션 저장
    session_id = await db.save_user_session(github_user, access_token)

    # 4. session_id만 프런트엔드에 전달 (access_token 비노출)
    return RedirectResponse(url=f"{FRONTEND_URL}/?session_id={session_id}")


@router.get("/auth/me")
async def get_current_user(session_id: str):
    """session_id로 현재 로그인된 유저 정보 반환."""
    session = await db.get_user_session(session_id)
    
    if not session:
        raise HTTPException(status_code=401, detail="세션이 만료되었거나 유효하지 않습니다")
    
    return {
        "github_user": session["github_user"],
        "github_id": session["github_id"],
        "avatar_url": session.get("avatar_url"),
        "session_id": session["session_id"]
    }


@router.post("/auth/logout")
async def logout(session_id: str):
    """세션 삭제 (로그아웃)."""
    await db.delete_user_session(session_id)
    return {"message": "로그아웃 완료"}


@router.get("/user/repos", response_model=List[Repo])
async def get_user_repos(session_id: str):
    """
    session_id를 사용하여 유저의 GitHub 리포지토리 목록 조회.
    MongoDB에 저장된 access_token을 내부적으로 사용.
    """
    # 1. 세션에서 access_token 가져오기
    session = await db.get_user_session(session_id)
    
    if not session:
        raise HTTPException(status_code=401, detail="세션이 만료되었거나 유효하지 않습니다")
    
    access_token = session["access_token"]

    # 2. GitHub API로 리포지토리 목록 가져오기
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.github.com/user/repos",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github.v3+json"
            },
            params={
                "sort": "updated",
                "per_page": 100,
                "type": "all"
            }
        )
        
        if response.status_code == 401:
            raise HTTPException(status_code=401, detail="GitHub 토큰이 만료되었습니다. 다시 로그인해주세요.")
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Failed to fetch repos")

        repos_data = response.json()
        
    repos = [
        Repo(
            id=r["id"],
            name=r["name"],
            full_name=r["full_name"],
            html_url=r["html_url"],
            description=r.get("description"),
            private=r["private"],
            language=r.get("language")
        )
        for r in repos_data
    ]
    
    return repos
