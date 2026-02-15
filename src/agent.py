from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from src.legacy.zap_scanner import zap_scanner
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
                "other": a.get('other', '')[:1000] 
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
def generate_local_expert_fix(vulnerable_code: str) -> str:
    """
    Generates a secure code fix using a specialized local Small Language Model (Repair_Model_v4).
    Input: Vulnerable source code string.
    Output: Secure code suggestion.
    Use this as a secondary 'expert opinion' to compare with your own reasoning.
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

tools = [run_security_scan, verify_vulnerability, generate_local_expert_fix, search_past_solutions]

# 2. Setup LLM & Prompt
llm = ChatOpenAI(model="gpt-4o", temperature=0)

prompt = ChatPromptTemplate.from_messages([
    ("system", """You are RedEye, an elite AI Security Engineer powered by GPT-4o.
Your goal is to inspect a target (URL or Repository), find vulnerabilities, verify them, and provide high-quality secure fixes.

Process:
1. Scan the target using `run_security_scan`.
2. Analyze found vulnerabilities.
3. VERIFY suspected code using `verify_vulnerability` to reduce false positives.
4. For verified vulnerabilities:
   - First, think of a secure fix yourself using your advanced knowledge.
   - Optionally, call `generate_local_expert_fix` to get a second opinion from a specialized local model.
   - Combine these insights to provide the best possible fix.
5. Search for past solutions using `search_past_solutions`.
6. Compile a final comprehensive report.

The final report MUST be in Markdown.
"""),
    ("user", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

# 3. Create Agent
agent = create_openai_tools_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
