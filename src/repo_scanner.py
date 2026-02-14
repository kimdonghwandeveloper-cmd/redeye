import os
import shutil
import tempfile
import re
from git import Repo
from typing import List, Dict, Any

class RepoScanner:
    """
    RepoScanner handles Static Application Security Testing (SAST) using pattern matching.
    It can scan:
    1. GitHub Repositories (via `scan_repo`) - Clones and scans all files.
    2. Raw Code Content (via `scan_content`) - Scans a single code snippet (API use).
    """
    def __init__(self):
        self.vulnerability_patterns = [
            # 1. Hardcoded Secrets (AWS, Generic API Keys)
            {
                "pattern": r"(?i)(aws_access_key_id|aws_secret_access_key|api_key|secret_key)[\s]*=[\s]*['\"][A-Za-z0-9/\+=]{15,}['\"]",
                "label": "Hardcoded Secret",
                "risk": "High",
                "description": "Possible hardcoded API key or secret found. Never commit secrets to version control."
            },
            # 2. SQL Injection (Broader Pattern)
            {
                "pattern": r"(?i)(SELECT|INSERT|UPDATE|DELETE).*['\"]\s*\+\s*[a-zA-Z_][a-zA-Z0-9_]*",
                "label": "SQL Injection",
                "risk": "High",
                "description": "Potential SQL Injection via string concatenation detected."
            },
            # 3. Unsafe Deserialization
            {
                "pattern": r"(?i)pickle\.loads\(",
                "label": "Unsafe Deserialization",
                "risk": "High",
                "description": "Usage of pickle.loads() is insecure if input is untrusted."
            },
            # 4. Debug Mode Enabled
            {
                "pattern": r"(?i)debug\s*=\s*True",
                "label": "Debug Mode Enabled",
                "risk": "Medium",
                "description": "Debug mode should be disabled in production."
            },
             # 5. Generic TODOs (Low Risk)
            {
                "pattern": r"(?i)#\s*TODO",
                "label": "TODO Comment",
                "risk": "Low",
                "description": "Found TODO comment. Check if it indicates incomplete security features."
            }
        ]

    def scan_content(self, content: str, filename: str = "snippet") -> List[Dict[str, Any]]:
        """
        Scans a single string of code for vulnerabilities.
        Useful for API endpoints where code is sent directly.
        """
        alerts = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            for vuln in self.vulnerability_patterns:
                if re.search(vuln["pattern"], line):
                    # Capture Context (+/- 2 lines)
                    start_line = max(0, i - 2)
                    end_line = min(len(lines), i + 3)
                    context_lines = lines[start_line:end_line]
                    context_snippet = "\n".join(context_lines)

                    alerts.append({
                        "alert": vuln["label"],
                        "risk": vuln["risk"],
                        "description": vuln["description"],
                        "other": f"File: {filename}:{i+1}\nCode:\n{context_snippet}"[:500] 
                    })
        return alerts

    def scan_repo(self, repo_url: str) -> List[Dict[str, Any]]:
        """
        Clones the repo to a temp dir, scans files, and returns alerts.
        Legacy method: In RedEye 3.0, n8n handles cloning. This is kept for backward compatibility.
        """
        print(f"🔍 [SAST] Cloning {repo_url}...")
        temp_dir = tempfile.mkdtemp()
        alerts = []

        try:
            Repo.clone_from(repo_url, temp_dir, depth=1)
            
            # Walk through files
            for root, dirs, files in os.walk(temp_dir):
                if ".git" in dirs:
                    dirs.remove(".git") # Skip .git dir
                
                for file in files:
                    file_path = os.path.join(root, file)
                    
                    # Skip binary or non-code files
                    if not self._is_code_file(file):
                        continue
                        
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            # Use the shared scanning logic
                            file_alerts = self.scan_content(content, filename=file)
                            alerts.extend(file_alerts)
                    except Exception as read_err:
                        print(f"⚠️ Failed to read {file}: {read_err}")

        except Exception as e:
            print(f"❌ [SAST] Failed to scan repo: {e}")
            alerts.append({
                "alert": "Scan Error",
                "risk": "Low",
                "description": f"Failed to clone or scan repository: {str(e)}",
                "other": ""
            })
        finally:
            # Cleanup
            shutil.rmtree(temp_dir, ignore_errors=True)
            print(f"🧹 [SAST] Verified & Cleaned up temp dir: {temp_dir}")

        return alerts

    def _is_code_file(self, filename: str) -> bool:
        allowed_extensions = {'.py', '.js', '.ts', '.java', '.c', '.cpp', '.cs', '.go', '.rb', '.php', '.html', '.env'}
        return any(filename.endswith(ext) for ext in allowed_extensions)

repo_scanner = RepoScanner()
