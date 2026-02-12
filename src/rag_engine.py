from langchain_mongodb import MongoDBAtlasVectorSearch
from langchain_openai import OpenAIEmbeddings
from pymongo import MongoClient
from .config import settings

class RAGService:
    def __init__(self):
        self.embeddings = OpenAIEmbeddings()
        self.vector_store = None
        self.collection_name = "vulnerability_vectors"
        self.client = None

    async def initialize(self):
        """Initialize the vector store with the MongoDB collection (Sync for LangChain compatibility)."""
        # LangChain MongoDB vector store works best with PyMongo for now
        self.client = MongoClient(settings.MONGO_URI)
        collection = self.client[settings.DB_NAME][self.collection_name]
        
        self.vector_store = MongoDBAtlasVectorSearch(
            collection=collection,
            embedding=self.embeddings,
            index_name="default",
            relevance_score_fn="cosine",
        )
        print("✅ RAG Service Initialized (Sync PyMongo)")

    async def ingest_alert(self, alert_text: str, metadata: dict):
        """Save a vulnerability alert to the vector store."""
        if self.vector_store:
            # add_texts is sync in LangChain standard, but might be async supported?
            # actually asimilarity_search implies async support, but let's stick to standard methods.
            # If using sync client, we should probably use sync add_texts. 
            # But the method is async def. We can run it in executor or just call sync method if it's fast.
            # aadd_texts is the async version.
            await self.vector_store.aadd_texts(
                texts=[alert_text],
                metadatas=[metadata]
            )
            print(f"📥 Ingested alert: {alert_text[:50]}...")

    async def search_similar_alerts(self, query: str, k: int = 3):
        """Search for similar past alerts."""
        if not self.vector_store:
            return []
        
        # asimilarity_search should work if the vector store supports it. 
        # With PyMongo (sync), asimilarity_search usually delegates to run_in_executor.
        results = await self.vector_store.asimilarity_search(query, k=k)
        return results

rag_service = RAGService()

