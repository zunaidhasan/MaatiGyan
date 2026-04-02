"""
MaatiGyan — RAG Data Ingestion Script
Loads fertilizer recommendation corpus into Qdrant Vector DB.
"""
import logging
import os
import sys

# Add parent directory to path so we can import config
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from backend.config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Ingestor")

def main():
    settings = get_settings()
    
    try:
        from llama_index.core import VectorStoreIndex, StorageContext, Settings, SimpleDirectoryReader
        from llama_index.embeddings.huggingface import HuggingFaceEmbedding
        from llama_index.vector_stores.qdrant import QdrantVectorStore
        import qdrant_client

        logger.info(f"Loading documents from: {settings.data_dir}")
        
        # 1. Load documents
        reader = SimpleDirectoryReader(settings.data_dir, filename_as_id=True)
        documents = reader.load_data()
        logger.info(f"Loaded {len(documents)} document pages")

        # 2. Configure Embedding Model (Local)
        logger.info("Initializing embedding model (BAAI/bge-small-en)...")
        embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en")
        Settings.embed_model = embed_model
        Settings.chunk_size = 512

        # 3. Configure Qdrant
        logger.info(f"Connecting to Qdrant at: {settings.qdrant_url}")
        if settings.qdrant_url == ":memory:":
            qclient = qdrant_client.QdrantClient(location=":memory:")
        else:
            qclient = qdrant_client.QdrantClient(
                url=settings.qdrant_url,
                api_key=settings.qdrant_api_key or None,
            )

        vector_store = QdrantVectorStore(
            client=qclient, 
            collection_name=settings.qdrant_collection
        )
        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        # 4. Create index and persist (if not in-memory)
        logger.info("Creating vector index...")
        VectorStoreIndex.from_documents(
            documents, 
            storage_context=storage_context,
            show_progress=True
        )

        logger.info("✅ Data ingestion complete!")

    except ImportError as e:
        logger.error(f"Missing dependency: {e}. Run: pip install llama-index qdrant-client sentence-transformers")
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")

if __name__ == "__main__":
    main()
