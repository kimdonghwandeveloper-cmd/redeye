from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from src.zap_scanner import zap_scanner
from src.expert_model import expert_model
from src.rag_engine import rag_service
import json
import os

from src.repo_scanner import repo_scanner

# 1. Define Tools
@tool
async def run_security_scan(target: str) -> str:
    """
    Scans a target (URL or GitHub Repo) for security vulnerabilities.
    - If target is a GitHub Repo: Uses Static Analysis (SAST) to find secrets & code issues.
    - If target is a Web URL: Uses OWASP ZAP (DAST) to find runtime vulnerabilities.
    Returns a list of alerts in JSON format.
    """
    if "github.com" in target:
        # SAST Path
        print(f"🔄 Routing to Repo Scanner: {target}")
        alerts = repo_scanner.scan_repo(target)
    else:
        # DAST Path
        print(f"🔄 Routing to ZAP Scanner: {target}")
        alerts = await zap_scanner.scan(target)

    # Simplify alerts to save context window
    simple_alerts = []
    for a in alerts:
        # Filter: For SAST, include all. For ZAP, only High/Medium unless empty.
        risk = a.get('risk', 'Low')
        if risk in ['High', 'Medium'] or "github.com" in target:
             simple_alerts.append({
                "alert": a.get('alert'),
                "risk": risk,
                "description": a.get('description')[:200], 
                "other": a.get('other', '')[:300] 
            })
            
    return json.dumps(simple_alerts)

@tool
def verify_vulnerability(code_snippet: str) -> str:
    """
    Verifies if a code snippet is truly vulnerable using a specialized AI model (Expert_Detector).
    Input: Source code string.
    Output: Prediction (SAFE or VULNERABLE) and confidence score.
    Use this to reduce false positives.
    """
    result = expert_model.verify(code_snippet)
    return json.dumps(result)

@tool
def generate_fix(vulnerable_code: str) -> str:
    """
    Generates a secure code fix for a vulnerable code snippet using a specialized AI model (Repair_Model).
    Input: Vulnerable source code string.
    Output: Secure code suggestion.
    """
    fix = expert_model.repair(vulnerable_code)
    return fix

@tool
async def search_past_solutions(query: str) -> str:
    """
    Searches the RAG database for similar past vulnerabilities and their solutions.
    Input: Description of the vulnerability or alert name.
    Output: List of similar past cases.
    """
    try:
        results = await rag_service.search_similar_alerts(query)
        output = []
        for doc in results:
            output.append(doc.page_content[:300]) # Truncate
        return "\n---\n".join(output) if output else "No past similar incidents found."
    except Exception as e:
        print(f"⚠️ RAG Search Failed (DB Offline?): {e}")
        return "No similar past incidents found. (RAG Search unavailable)"

tools = [run_security_scan, verify_vulnerability, generate_fix, search_past_solutions]

# 2. Setup LLM & Prompt
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

prompt = ChatPromptTemplate.from_messages([
    ("system", """You are RedEye, an elite AI Security Engineer.
Your goal is to inspect a target (URL or Repository), find vulnerabilities, verify them, and suggest fixes.

Process:
1. Scan the target using `run_security_scan`.
   - If it's a GitHub Repo, this performs Static Analysis (secrets, patterns).
   - If it's a Web URL, this performs Dynamic Analysis (ZAP).
2. If vulnerabilities are found, analyze them.
3. If specific code snippets are available (especially from SAST), VERIFY them using `verify_vulnerability`.
   - If SAFE: Be skeptical.
   - If VULNERABLE: Proceed to fix.
4. If a vulnerability is verified, use `generate_fix` to create a patch.
5. Search for past solutions using `search_past_solutions`.
6. Compile a final comprehensive report.

The final report should be in Markdown.

IMPORTANT:
If `run_security_scan` returns an empty list or only informative/low alerts that are not actionable:
1. State clearly that no significant vulnerabilities were detected.
2. Set "current_score" to 100.
3. Set "risk_breakdown" to an empty list [].
4. Do NOT invent or hallucinate vulnerabilities.

At the very end of your response, you MUST append a JSON block wrapped in ```json tags.
This JSON block contains the quantative security analysis.
Format:
```json
{{
  "current_score": <0-100 integer>,
  "projected_score": <0-100 integer>,
  "risk_breakdown": [
    {{"vulnerability": "Hardcoded Secret", "impact": -30, "fix_improvement": +30}}
    // Leave this list EMPTY if no vulnerabilities are found.
  ]
}}
```
Calculate the score: Start at 100. Deduct points for each vulnerability (High: -20, Medium: -10, Low: -5).
projected_score should be 100 if current_score is 100.
"""),
    ("user", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

# 3. Create Agent
agent = create_openai_tools_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
