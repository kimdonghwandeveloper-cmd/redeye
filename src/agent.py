from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from src.zap_scanner import zap_scanner
from src.expert_model import expert_model
from src.rag_engine import rag_service
import json
import os

# 1. Define Tools
@tool
async def run_zap_scan(target_url: str) -> str:
    """
    Scans a target URL using OWASP ZAP to find security vulnerabilities.
    Returns a JSON string of alerts. Use this tool first.
    """
    alerts = await zap_scanner.scan(target_url)
    # Simplify alerts to save context window
    simple_alerts = []
    for a in alerts:
        if a.get('risk') in ['High', 'Medium']:
            simple_alerts.append({
                "alert": a.get('alert'),
                "risk": a.get('risk'),
                "description": a.get('description')[:200], # Truncate
                "other": a.get('other', '')[:100] # Often contains code snippet
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
    result = expert_model.predict(code_snippet)
    return json.dumps(result)

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
        return "MOCK SOLUTION: Use parameterized queries to prevent SQL Injection. (Database connection failed, using fallback knowledge.)"

tools = [run_zap_scan, verify_vulnerability, search_past_solutions]

# 2. Setup LLM & Prompt
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

prompt = ChatPromptTemplate.from_messages([
    ("system", """You are RedEye, an elite AI Security Engineer.
Your goal is to inspect a target URL, find vulnerabilities, verify them, and suggest fixes.

Process:
1. Scan the target URL using `run_zap_scan`.
2. If vulnerabilities are found, analyze them.
3. If specific code snippets are available in the alert (e.g. in 'other' field), VERIFY them using `verify_vulnerability` to check if they are real or false positives.
   - If the model says SAFE, be skeptical of the scanner's result.
   - If the model says VULNERABLE, proceed with high confidence.
4. Search for past solutions using `search_past_solutions` to see how we fixed similar issues before.
5. Compile a final comprehensive report.

The final report should be in Markdown, listing each vulnerability with:
- Severity
- Verification Status (Verified by AI / Potential False Positive)
- Suggested Fix (referencing past solutions if available)
"""),
    ("user", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

# 3. Create Agent
agent = create_openai_tools_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
