import os
from typing import List, Dict
from langchain_openai import OpenAIEmbeddings
from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_core.documents import Document
from .database import db

class RAGService:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        self.vector_store = None

    def initialize(self):
        """Must be called after db.connect()"""
        if db.get_db() is not None:
            collection = db.get_db()["scans"]
            # MongoDB Atlas Vector Search Setup
            self.vector_store = MongoDBAtlasVectorSearch(
                collection=collection,
                embedding=self.embeddings,
                index_name="vector_index", # The name you typed in Atlas UI
                relevance_score_fn="cosine",
            )
            print("🧠 RAG Engine Initialized (MongoDB Atlas)")
        else:
            print("⚠️ DB not connected. RAG disabled.")

    async def ingest_alerts(self, alerts: List[Dict]):
        """Save new alerts to Vector DB for future reference"""
        if not self.vector_store:
            return

        documents = []
        for alert in alerts:
            # Create a rich text representation for embedding
            content = f"Risk: {alert.get('risk')}\nName: {alert.get('name')}\nDescription: {alert.get('description')}\nSolution: {alert.get('solution')}"
            
            # Metadata for filtering/reference
            metadata = {
                "risk": alert.get("risk"),
                "name": alert.get("name"),
                "url": alert.get("url"),
                "scan_id": alert.get("scan_id", "unknown")
            }
            
            documents.append(Document(page_content=content, metadata=metadata))

        if documents:
            # Add documents to vector store (This is blocking in LangChain default, but fast enough for small batches)
            # ideally, run in executor if heavy.
            self.vector_store.add_documents(documents)
            print(f"📥 Ingested {len(documents)} alerts into Knowledge Base.")

    async def search_similar_issues(self, query_text: str, k: int = 3) -> List[Document]:
        """Retrieve similar past vulnerabilities"""
        if not self.vector_store:
            return []
        
        # Async search provided by langchain-mongodb?
        # Current version often sync, but let's try standard invocation or invoke in thread if needed.
        # Motor is async, but LangChain's wrapper might block. For now, we assume it's acceptable or wrapped.
        
        # NOTE: langchain-mongodb usually uses synchronous pymongo or wraps it? 
        # Actually MongoDBAtlasVectorSearch uses pymongo (sync) by default.
        # Ideally we should use `asimilarity_search` if available, or run in thread.
        
        try:
            results = self.vector_store.similarity_search(query_text, k=k)
            return results
        except Exception as e:
            print(f"❌ Vector Search Error: {e}")
            return []

rag_engine = RAGService()
