import os
import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

# Configuration
GITHUB_CLIENT_ID = os.getenv("CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("CLIENT_SECRET")
# Determine callback URL based on environment (local vs prod)
# We can infer it from the request or set via env var. 
# For now, let's hardcode localhost for dev, but we should make it configurable.
# Better: use the Host header from the request to build the callback URL dynamically?
# No, GitHub requires exact match.
# Let's assume env var or default to localhost.
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8000") 
CALLBACK_URL = f"{APP_BASE_URL}/auth/github/callback"

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
    """
    Redirects the user to GitHub's OAuth consent page.
    """
    if not GITHUB_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Server misconfigured: Missing GITHUB_CLIENT_ID")
    
    scope = "read:user repo" # 'repo' scope needed for private repos
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
    Exchanges the temporary code for an access token.
    Then redirects to the frontend with the token (or sets a cookie).
    """
    if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
         raise HTTPException(status_code=500, detail="Server misconfigured: Missing Credentials")

    # 1. Exchange code for access token
    token_url = "https://github.com/login/oauth/access_token"
    headers = {"Accept": "application/json"}
    data = {
        "client_id": GITHUB_CLIENT_ID,
        "client_secret": GITHUB_CLIENT_SECRET,
        "code": code,
        "redirect_uri": CALLBACK_URL
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, json=data, headers=headers)
        if response.status_code != 200:
             raise HTTPException(status_code=400, detail="Failed to retrieve access token from GitHub")
        
        token_data = response.json()
        if "error" in token_data:
             raise HTTPException(status_code=400, detail=f"GitHub Error: {token_data.get('error_description')}")
        
        access_token = token_data.get("access_token")

    # 2. Redirect to Frontend with Token
    # In a real app, we might create a session here. 
    # For MVP, we pass the token to the frontend via query param (simple but risky) 
    # or set a cookie.
    # Let's redirect to the frontend root with the token in URL fragment/query
    
    # Frontend URL (assumed localhost:5173 for dev)
    # We should probably use an env var for frontend URL
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173") 
    
    return RedirectResponse(url=f"{FRONTEND_URL}/?github_token={access_token}")

@router.get("/user/repos", response_model=List[Repo])
async def get_user_repos(token: str):
    """
    Fetches the list of repositories for the authenticated user.
    """
    if not token:
        raise HTTPException(status_code=401, detail="Missing GitHub Token")

    api_url = "https://api.github.com/user/repos"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    params = {
        "sort": "updated",
        "per_page": 100,
        "type": "all" # owner, public, private, member
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(api_url, headers=headers, params=params)
        
        if response.status_code == 401:
             raise HTTPException(status_code=401, detail="Invalid or expired GitHub Token")
        if response.status_code != 200:
             raise HTTPException(status_code=response.status_code, detail="Failed to fetch repos from GitHub")

        repos_data = response.json()
        
    # Map to our schema
    repos = []
    for r in repos_data:
        repos.append(Repo(
            id=r["id"],
            name=r["name"],
            full_name=r["full_name"],
            html_url=r["html_url"],
            description=r.get("description"),
            private=r["private"],
            language=r.get("language")
        ))
        
    return repos
