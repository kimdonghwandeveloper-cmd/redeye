import langchain
import langchain.agents
import sys

print(f"Python Version: {sys.version}")
print(f"LangChain Version: {langchain.__version__}")
try:
    import langchain_community
    print(f"LangChain Community Version: {langchain_community.__version__}")
except ImportError:
    print("LangChain Community not installed")

print("\n--- langchain.agents contents ---")
print(dir(langchain.agents))

print("\n--- Attempting Import ---")
try:
    from langchain.agents import AgentExecutor
    print("✅ Success: from langchain.agents import AgentExecutor")
except ImportError as e:
    print(f"❌ Failed: {e}")
