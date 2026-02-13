# RedEye 2.0: AI 기반 취약점 스캐너 (AI-Powered Vulnerability Scanner)

![RedEye AI](https://img.shields.io/badge/Security-AI%20Powered-red) ![Python](https://img.shields.io/badge/Backend-FastAPI-green) ![React](https://img.shields.io/badge/Frontend-React-blue) ![Status](https://img.shields.io/badge/Status-MVP%20Complete-success)

**RedEye 2.0**은 기존의 취약점 스캐너(DAST/SAST)에 **AI 검증(AI Verification)** 기술을 결합한 차세대 보안 플랫폼입니다. 수많은 오탐(False Positive)을 쏟아내는 기존 도구들과 달리, RedEye는 파인튜닝된 LLM을 통해 **취약점의 진위 여부를 검증**하고 **안전한 수정 코드**까지 제안합니다.

---

## ✨ 핵심 기능 (Key Features)

### 1. 🛡️ 이중 스캔 엔진 (Dual Scanning Engine)
- **웹 스캔 (DAST):** **OWASP ZAP**을 연동하여 실제 운영 중인 웹사이트의 런타임 취약점(XSS, SQL Injection 등)을 탐지합니다.
- **리포지토리 스캔 (SAST):** GitHub 소스코드를 정적으로 분석하여 코드 레벨의 결함(하드코딩된 비밀키, 취약한 함수 사용 등)을 찾아냅니다.

### 2. 🧠 AI 문맥 검증 (Context-Aware Verification)
- **문제점:** 단순 패턴 매칭 방식은 안전한 코드도 위험하다고 오판하는 경우가 많습니다.
- **해결책:** RedEye는 취약점이 의심되는 코드뿐만 아니라 **주변 문맥(앞뒤 2줄)**을 함께 추출하여 AI에게 *"이게 진짜 공격 가능한가?"* 라고 물어봅니다.
- **결과:** 오탐률을 획기적으로 낮추고 분석의 정확도를 높였습니다.

### 3. 🔧 AI 자동 수정 (AI Auto-Repair)
- 검증된 취약점에 대해 **Repair Model (T5 + LoRA)**이 즉시 적용 가능한 **보안 패치 코드**를 생성하여 제안합니다.

### 4. 🐙 GitHub 통합 (GitHub Integration)
- GitHub 계정으로 간편하게 로그인하세요.
- 사용자의 **비공개(Private) 리포지토리** 목록을 불러와 클릭 한 번으로 보안 검사를 수행할 수 있습니다.

### 5. 📉 클라우드 최적화 (Cloud Optimization)
- **Railway (Starter Plan)** 환경에서도 원활히 동작하도록 설계되었습니다.
- **동적 8-bit 양자화:** AI 모델 크기를 500MB 이하로 압축했습니다.
- **Lazy Loading (지연 로딩):** 평소엔 메모리를 비워두고, 분석이 필요할 때만 모델을 로드하여 리소스를 절약합니다.

---

## 🏗️ 아키텍처 (Architecture)

| 컴포넌트 | 기술 스택 | 설명 |
| :--- | :--- | :--- |
| **Frontend** | React, Vite, Chakra UI | 반응형 대시보드 및 결과 리포트 뷰어 |
| **Backend** | FastAPI, Python 3.10 | 비동기 API 서버, 비즈니스 로직, AI 오케스트레이션 |
| **Database** | MongoDB Atlas | 스캔 결과 및 세션 데이터 저장 (Stateless Users) |
| **AI Engine** | PyTorch, Transformers | **탐지:** CodeBERT (Fine-tuned)<br>**수정:** T5-Small + LoRA |
| **Scanner** | OWASP ZAP (Docker) | DAST 엔진 (Sidecar 컨테이너로 구동) |

---

## 🚀 설치 및 실행 가이드 (Installation & Setup)

### 사전 요구사항 (Prerequisites)
- Python 3.10 이상
- Node.js 18 이상
- MongoDB (Atlas 또는 로컬 설치)
- Docker (ZAP 실행용, 로컬 개발 시 선택 사항)

### 1. 백엔드 설정 (Backend Setup)
```bash
# 리포지토리 클론
git clone https://github.com/kimdonghwandeveloper/redeye.git
cd redeye

# 가상환경 생성 및 활성화
python -m venv venv
# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

# 의존성 패키지 설치
pip install -r requirements.txt

# 환경 변수 설정 (.env)
cp .env.example .env
# .env 파일에 OPENAI_API_KEY, MONGO_URI, GITHUB_CLIENT_ID 등을 입력하세요.
```

### 2. 프론트엔드 설정 (Frontend Setup)
```bash
cd frontend
npm install
npm run dev
```

### 3. 애플리케이션 실행 (Run Application)
```bash
# 백엔드 실행 (루트 경로에서)
uvicorn main:app --reload

# 프론트엔드 실행 (frontend 경로에서)
npm run dev
```
이제 브라우저에서 `http://localhost:5173`으로 접속하여 RedEye를 사용해보세요!

---

## 📖 사용 방법 (Usage)

1.  **로그인:** GitHub 계정으로 로그인하여 리포지토리 접근 권한을 얻습니다.
2.  **스캔 시작:**
    *   **URL 모드:** 웹사이트 주소(예: `http://testphp.vulnweb.com`)를 입력하여 XSS/SQLi 취약점을 동적으로 검사합니다.
    *   **Repo 모드:** 본인의 GitHub 리포지토리를 선택하여 소스코드 보안 분석을 수행합니다.
3.  **결과 확인:**
    *   **안전 점수(Safety Score)** 게이지를 확인하세요.
    *   **검증된 취약점** 목록을 상세히 살펴봅니다.
    *   **AI 분석 결과**와 **수정 제안 코드**를 참고하여 보안을 강화합니다.

---

## 🔮 향후 로드맵 (Roadmap)
- [ ] **DB 영구 저장:** 사용자별 스캔 이력을 영구적으로 보관.
- [ ] **PDF 리포트:** 전문적인 보안 보고서 파일(PDF) 다운로드 기능.
- [ ] **IDE 플러그인:** VS Code 등에서 코딩 중에 실시간으로 보안 가이드를 제공하는 확장 프로그램 개발.

---

## 📝 라이선스 (License)
이 프로젝트는 **MIT License**를 따릅니다.

---
*Built with ❤️ by the RedEye Team*
