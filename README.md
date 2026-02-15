# RedEye: AI Security Agent

![RedEye AI](https://img.shields.io/badge/Security-AI%20Powered-red) ![Python](https://img.shields.io/badge/Backend-FastAPI-green) ![React](https://img.shields.io/badge/Frontend-React-blue) ![n8n](https://img.shields.io/badge/Automation-n8n-orange) ![Railway](https://img.shields.io/badge/Deploy-Railway-purple)

**RedEye**는 AI 에이전트가 보안 취약점을 **탐지 → 검증 → 수정**까지 자동으로 수행하는 차세대 보안 플랫폼입니다.

기존 보안 스캐너(ZAP, Semgrep 등)는 오탐(False Positive)이 많아 개발자가 일일이 확인해야 합니다. RedEye는 **파인튜닝된 AI 모델**로 취약점의 진위 여부를 검증하고, **자동 수정 코드**까지 생성합니다. **n8n 워크플로우**와 연동하면 PR이 올라갈 때마다 자동으로 보안 리뷰를 수행합니다.

---

## 🏗️ 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    🌐 GitHub Webhook                        │
│               (PR 생성 시 자동 트리거)                         │
└──────────────────────┬──────────────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────────────┐
│                   ⚡ n8n Workflow Engine                      │
│  [Webhook] → [RedEye API 호출] → [결과 포맷팅] → [PR Comment]  │
└──────────────────────┬──────────────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────────────┐
│              🔴 RedEye API (FastAPI)                          │
│                                                              │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐    │
│  │ SAST Scanner │  │ AI Detection │  │ AI Repair Model  │    │
│  │ (Regex+Git)  │  │ (CodeBERT)   │  │ (T5-Small+LoRA)  │    │
│  └─────────────┘  └──────────────┘  └──────────────────┘    │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ LangChain    │  │ RAG Engine   │  │ GitHub Diff API  │   │
│  │ Agent(GPT-4o)│  │ (Vector DB)  │  │ (CodeRabbit방식)  │   │
│  └──────────────┘  └──────────────┘  └──────────────────┘   │
└──────────────────────┬──────────────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────────────┐
│  📊 React Dashboard     │     🗄️ MongoDB Atlas              │
│  (Chakra UI, Recharts)  │  (스캔 결과, 세션, RAG 벡터)        │
└──────────────────────────────────────────────────────────────┘
```

---

## ✨ 핵심 기능

### 1. 🤖 AI 에이전트 기반 보안 분석
GPT-4o-mini 기반의 LangChain 에이전트가 4가지 도구를 조합하여 자율적으로 보안 분석을 수행합니다:

| 도구 | 기능 | 모델/기술 |
|------|------|----------|
| `run_security_scan` | 정적/동적 취약점 탐지 | SAST (Regex), DAST (OWASP ZAP) |
| `verify_vulnerability` | 코드 스니펫의 취약 여부 검증 | CodeBERT (Fine-tuned) |
| `generate_fix` | 취약한 코드의 보안 패치 생성 | T5-Small + LoRA |
| `search_past_solutions` | 유사 취약점 과거 사례 검색 | MongoDB Atlas Vector Search |

### 2. 🔄 n8n 자동화 (CI/CD 보안 통합)
- GitHub에 PR이 올라오면 **n8n Webhook**이 자동으로 RedEye API를 호출
- 변경된 파일만 **GitHub Diff API**로 효율적으로 분석 (CodeRabbit 방식)
- 분석 결과를 **PR 코멘트**로 자동 게시

### 3. 🔐 GitHub OAuth + MongoDB 세션
- GitHub 로그인 → 액세스 토큰을 **MongoDB에 안전하게 저장**
- `session_id`만 프런트엔드에 전달 (토큰 비노출)
- localStorage로 새로고침 후에도 **로그인 유지**

### 4. 📉 클라우드 최적화
- Railway Starter Plan (8GB RAM)에서 동작하도록 설계
- AI 모델 **동적 8-bit 양자화** (500MB 이하)
- **Lazy Loading**: 분석 요청 시에만 모델 로드

---

## 📁 프로젝트 구조

```
redeye/
├── main.py                      # FastAPI 앱 진입점 (라이프사이클, 라우터)
├── pyproject.toml               # uv 의존성 관리
│
├── src/
│   ├── agent.py                 # LangChain AI 에이전트 (GPT-4o-mini + 4 Tools)
│   ├── repo_scanner.py          # SAST 스캐너 (정규식 기반 코드 분석)
│   ├── github_diff_scanner.py   # GitHub Diff API 기반 PR 스캐너
│   ├── expert_model.py          # AI 모델 (CodeBERT 탐지 + T5 수정)
│   ├── rag_engine.py            # RAG 벡터 검색 (MongoDB Atlas)
│   ├── database.py              # MongoDB 연결 및 세션 관리
│   ├── config.py                # 환경변수 설정 (Pydantic Settings)
│   │
│   ├── api/
│   │   └── analysis.py          # n8n용 분석 API (/analyze/pr, /analyze/code)
│   ├── auth/
│   │   └── github.py            # GitHub OAuth (/auth/login, /auth/me, /auth/logout)
│   └── legacy/
│       └── zap_scanner.py       # OWASP ZAP DAST 스캐너
│
├── frontend/
│   └── src/
│       ├── App.tsx              # 라우팅 (Scanner, AI Models)
│       ├── ScanPage.tsx         # 메인 스캔 페이지 (GitHub 연동)
│       ├── api.ts               # 백엔드 API 클라이언트
│       └── pages/
│           └── ModelsPage.tsx   # AI 모델 학습 메트릭 대시보드
│
└── scripts/                     # 유틸리티 스크립트
```

---

## 🚀 설치 및 실행

### 사전 요구사항
- Python 3.10+
- Node.js 18+
- MongoDB Atlas 계정
- GitHub OAuth App (CLIENT_ID, CLIENT_SECRET)

### 1. 백엔드
```bash
git clone https://github.com/kimdonghwandeveloper-cmd/redeye.git
cd redeye

# uv 패키지 매니저 사용
pip install uv
uv sync

# 환경변수 설정
cp .env.example .env
# .env에 OPENAI_API_KEY, MONGODB_URI, CLIENT_ID, CLIENT_SECRET 등 입력

# 서버 실행
uv run uvicorn main:app --port 8000
```

### 2. 프론트엔드
```bash
cd frontend
npm install
npm run dev
```

### 3. 환경변수 (.env)
```env
OPENAI_API_KEY=sk-xxx
MONGODB_URI=mongodb+srv://...
GITHUB_TOKEN=ghp_xxx
HF_TOKEN=hf_xxx
CLIENT_ID=Ov23xxx
CLIENT_SECRET=xxx
DETECTION_MODEL_PATH=kimdonghwanAIengineer/redeye-detection-quantized
REPAIR_MODEL_PATH=kimdonghwanAIengineer/redeye-repair-quantized
```

---

## 🔗 API 엔드포인트

| Method | Path | 설명 |
|--------|------|------|
| `GET` | `/` | 서버 상태 확인 |
| `POST` | `/scan` | 전체 보안 스캔 시작 (비동기) |
| `GET` | `/scan/{scan_id}` | 스캔 상태/결과 조회 |
| `POST` | `/analyze/pr` | PR Diff 분석 (n8n용) |
| `POST` | `/analyze/code` | 코드 스니펫 분석 |
| `GET` | `/auth/github/login` | GitHub OAuth 로그인 |
| `GET` | `/auth/me` | 현재 로그인 유저 조회 |
| `POST` | `/auth/logout` | 로그아웃 |
| `GET` | `/user/repos` | 유저 GitHub 리포지토리 목록 |
| `GET` | `/models/metrics` | AI 모델 학습 메트릭 |

---

## 🤖 AI 모델 상세

### Detection Model (탐지)
- **Base:** `microsoft/codebert-base`
- **Fine-tuning:** CWE 취약점 데이터셋으로 학습
- **출력:** `SAFE` / `VULNERABLE` + 신뢰도 점수
- **최적화:** `bitsandbytes` 8-bit 양자화

### Repair Model (수정)
- **Base:** `t5-small`
- **Fine-tuning:** LoRA (Low-Rank Adaptation)
- **출력:** 보안 패치가 적용된 코드
- **최적화:** `bitsandbytes` 8-bit 양자화

---

## 🛣️ 로드맵

- [x] SAST/DAST 이중 스캔 엔진
- [x] AI 검증 (CodeBERT) + AI 수정 (T5+LoRA)
- [x] LangChain 에이전트 자율 분석
- [x] RAG 과거 사례 검색
- [x] GitHub OAuth + MongoDB 세션
- [x] n8n 워크플로우 자동화
- [ ] PDF 보안 리포트 다운로드
- [ ] VS Code 확장 프로그램
- [ ] 멀티 에이전트 (탐지 Agent + 수정 Agent 분리)

---

## 📝 라이선스
MIT License

---

*Built with ❤️ by RedEye Team*
