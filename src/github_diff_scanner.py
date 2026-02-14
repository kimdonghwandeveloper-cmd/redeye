import re
import aiohttp
from typing import List, Dict, Any
from src.repo_scanner import RepoScanner
from src.config import settings
import logging

logger = logging.getLogger(__name__)


class GitHubDiffScanner:
    """
    GitHub Diff API를 사용한 효율적인 PR 스캔 (CodeRabbit 방식)
    
    Git Clone 대신 GitHub API로 변경된 코드만 가져와서 분석합니다.
    - 네트워크 효율: 수백 MB → 수 KB
    - 속도: 수 분 → 몇 초
    - 정확성: 변경된 코드에만 집중
    """
    
    def __init__(self, github_token: str = None):
        self.github_token = github_token or settings.GITHUB_TOKEN
        self.repo_scanner = RepoScanner()  # 기존 패턴 매칭 재사용
        
        if not self.github_token:
            logger.warning("⚠️ GITHUB_TOKEN not set. API rate limits will be very restrictive.")
    
    async def scan_pr_diff(
        self, 
        owner: str, 
        repo: str, 
        pr_number: int,
        max_files: int = 50
    ) -> Dict[str, Any]:
        """
        GitHub PR의 변경된 코드만 스캔
        
        Args:
            owner: 리포지토리 소유자
            repo: 리포지토리 이름
            pr_number: PR 번호
            max_files: 최대 분석 파일 수 (Initial commit 대응)
        
        Returns:
            {
                "pr_number": int,
                "files_analyzed": int,
                "vulnerabilities": List[Dict],
                "summary": str
            }
        """
        try:
            # 1. GitHub API로 PR Files 가져오기
            logger.info(f"🔍 Fetching PR #{pr_number} from {owner}/{repo}...")
            files = await self._get_pr_files(owner, repo, pr_number)
            
            if not files:
                return {
                    "pr_number": pr_number,
                    "files_analyzed": 0,
                    "vulnerabilities": [],
                    "summary": "No files changed in this PR."
                }
            
            # 2. 파일 수 제한 (Initial commit 대비)
            if len(files) > max_files:
                logger.warning(f"⚠️ Large PR detected ({len(files)} files). Filtering to {max_files} important files...")
                files = self._filter_important_files(files, max_files)
            
            # 3. 변경된 라인만 추출
            changed_lines = self._parse_diff_patches(files)
            logger.info(f"📝 Extracted {len(changed_lines)} changed lines from {len(files)} files")
            
            # 4. 파일별로 그룹핑
            files_dict = {}
            for line_info in changed_lines:
                filename = line_info['filename']
                if filename not in files_dict:
                    files_dict[filename] = []
                files_dict[filename].append(line_info)
            
            # 5. 파일 단위로 분석 (전체 변경 내용을 컨텍스트로)
            all_vulnerabilities = []
            for filename, lines in files_dict.items():
                # 모든 변경된 라인을 하나의 코드 스니펫으로 합치기
                code_snippet = '\n'.join([line['code'] for line in lines])
                
                # scan_content()로 전체 스니펫 분석
                alerts = self.repo_scanner.scan_content(
                    code_snippet,
                    filename=filename
                )
                
                # 각 alert에 파일 정보 추가
                for alert in alerts:
                    alert['filename'] = filename
                    alert['change_type'] = 'added'  # 변경된 코드
                    all_vulnerabilities.append(alert)
            
            # 6. 결과 반환
            result = {
                "pr_number": pr_number,
                "repository": f"{owner}/{repo}",
                "files_analyzed": len(files),
                "lines_analyzed": len(changed_lines),
                "vulnerabilities": all_vulnerabilities,
                "summary": f"Found {len(all_vulnerabilities)} potential vulnerabilities in {len(files)} files."
            }
            
            logger.info(f"✅ PR scan complete: {len(all_vulnerabilities)} vulnerabilities found")
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to scan PR: {e}")
            raise
    
    async def _get_pr_files(self, owner: str, repo: str, pr_number: int) -> List[Dict]:
        """
        GitHub API로 PR의 변경된 파일 목록 가져오기
        
        GET /repos/{owner}/{repo}/pulls/{pr_number}/files
        """
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"
        headers = {
            'Accept': 'application/vnd.github.v3+json'
        }
        
        if self.github_token:
            headers['Authorization'] = f'token {self.github_token}'
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"GitHub API error ({response.status}): {error_text}")
                
                files = await response.json()
                return files
    
    def _parse_diff_patches(self, files: List[Dict]) -> List[Dict[str, Any]]:
        """
        GitHub Diff patch 파싱
        
        입력 예시:
        {
            "filename": "auth.py",
            "patch": "@@ -10,7 +10,8 @@\n-query = f\"SELECT...\"\n+query = \"SELECT...?\""
        }
        
        출력:
        [
            {
                "filename": "auth.py",
                "line_number": 11,
                "code": "query = \"SELECT...?\"",
                "change_type": "added"
            }
        ]
        """
        changed_lines = []
        
        for file in files:
            patch = file.get('patch', '')
            if not patch:
                continue
            
            filename = file['filename']
            lines = patch.split('\n')
            current_line = 0
            
            for line in lines:
                # @@ -10,7 +10,8 @@ 형식에서 시작 라인 추출
                if line.startswith('@@'):
                    match = re.match(r'@@ -\d+,?\d* \+(\d+)', line)
                    if match:
                        current_line = int(match.group(1))
                    continue
                
                # + 로 시작 = 추가된 코드 (보안 취약점은 보통 새로 추가된 코드에서 발생)
                if line.startswith('+') and not line.startswith('+++'):
                    changed_lines.append({
                        'filename': filename,
                        'line_number': current_line,
                        'code': line[1:],  # + 제거
                        'change_type': 'added'
                    })
                
                # 라인 번호 증가 (삭제된 라인은 제외)
                if not line.startswith('-'):
                    current_line += 1
        
        return changed_lines
    
    def _filter_important_files(self, files: List[Dict], max_files: int = 50) -> List[Dict]:
        """
        Initial commit 대응: 중요한 파일만 필터링
        
        보안 관련 키워드가 포함된 파일을 우선적으로 선택
        """
        # 보안 관련 우선순위 키워드
        priority_keywords = [
            'auth', 'login', 'password', 'secret', 'api_key', 'api-key',
            'token', 'credential', 'config', '.env', 'database', 'db',
            'security', 'crypto', 'hash', 'encrypt', 'session', 'cookie'
        ]
        
        important = []
        other = []
        
        for file in files:
            filename = file['filename'].lower()
            is_important = any(keyword in filename for keyword in priority_keywords)
            
            if is_important:
                important.append(file)
            else:
                other.append(file)
        
        # 우선순위 파일이 충분하면 우선순위만
        if len(important) >= max_files:
            logger.info(f"📌 Selected {max_files} priority files (security-related)")
            return important[:max_files]
        
        # 우선순위 파일 + 나머지 파일로 채우기
        remaining = max_files - len(important)
        logger.info(f"📌 Selected {len(important)} priority files + {remaining} other files")
        return important + other[:remaining]


# Singleton instance
github_diff_scanner = GitHubDiffScanner()
