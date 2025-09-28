import os
import logging
from typing import List, Dict, Any, Optional
from pinecone import Pinecone, ServerlessSpec
from langchain_pinecone import PineconeVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document

from .document_processor import DocumentProcessor
from ..config.pinecone_config import pinecone_config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VectorStoreManager:
    """Vector store manager using Hugging Face embeddings (free tier)."""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.pinecone_config = pinecone_config
        self.pinecone_config.validate()
        
        # Initialize Pinecone client
        self.pc = Pinecone(api_key=self.pinecone_config.api_key)
        
        # Initialize Hugging Face embeddings (completely free!)
        self.embeddings = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={'device': 'cpu'},  # Use CPU to avoid GPU requirements
            encode_kwargs={'normalize_embeddings': True}
        )
        
        self.vector_store = None
        self.index_name = self.pinecone_config.index_name
        self.model_name = model_name
        
        # Get embedding dimension based on model
        self.dimension = self._get_embedding_dimension()
    
    def _get_embedding_dimension(self) -> int:
        """Get the embedding dimension for the selected model."""
        # Common dimensions for popular models
        model_dimensions = {
            "sentence-transformers/all-MiniLM-L6-v2": 384,
            "sentence-transformers/all-mpnet-base-v2": 768,
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2": 384,
            "sentence-transformers/all-MiniLM-L12-v2": 384,
        }
        return model_dimensions.get(self.model_name, 384)  # Default to 384
    
    def create_index(self) -> bool:
        """Create Pinecone index if it doesn't exist."""
        try:
            # Check if index already exists
            existing_indexes = [index.name for index in self.pc.list_indexes()]
            
            if self.index_name in existing_indexes:
                logger.info(f"Index '{self.index_name}' already exists")
                return True
            
            # Create new index
            logger.info(f"Creating index '{self.index_name}' with dimension {self.dimension}...")
            
            # Use AWS for better free plan support
            self.pc.create_index(
                name=self.index_name,
                dimension=self.dimension,
                metric=self.pinecone_config.metric,
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1"
                )
            )
            
            logger.info(f"Index '{self.index_name}' created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error creating index: {str(e)}")
            return False
    
    def initialize_vector_store(self) -> bool:
        """Initialize the vector store connection."""
        try:
            self.vector_store = PineconeVectorStore(
                index_name=self.index_name,
                embedding=self.embeddings,
                pinecone_api_key=self.pinecone_config.api_key
            )
            logger.info("Vector store initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Error initializing vector store: {str(e)}")
            return False
    
    def populate_vector_store(self, docs_directory: str = "agents/docs") -> bool:
        """Populate the vector store with documents from the specified directory."""
        try:
            # Process documents
            processor = DocumentProcessor(docs_directory)
            documents = processor.process_all_documents()
            
            if not documents:
                logger.warning("No documents to process")
                return False
            
            # Convert to LangChain Document format
            langchain_docs = []
            for i, doc in enumerate(documents):
                langchain_doc = Document(
                    page_content=doc["content"],
                    metadata=doc["metadata"]
                )
                langchain_docs.append(langchain_doc)
            
            # Add documents to vector store
            logger.info(f"Adding {len(langchain_docs)} documents to vector store...")
            self.vector_store.add_documents(langchain_docs)
            
            logger.info("Vector store populated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error populating vector store: {str(e)}")
            return False
    
    def search_documents(self, query: str, k: int = 5) -> List[Document]:
        """Search for similar documents in the vector store."""
        try:
            if not self.vector_store:
                logger.error("Vector store not initialized")
                return []
            
            results = self.vector_store.similarity_search(query, k=k)
            logger.info(f"Found {len(results)} similar documents")
            return results
            
        except Exception as e:
            logger.error(f"Error searching documents: {str(e)}")
            return []
    
    def search_with_score(self, query: str, k: int = 5) -> List[tuple]:
        """Search for similar documents with similarity scores."""
        try:
            if not self.vector_store:
                logger.error("Vector store not initialized")
                return []
            
            results = self.vector_store.similarity_search_with_score(query, k=k)
            logger.info(f"Found {len(results)} similar documents with scores")
            return results
            
        except Exception as e:
            logger.error(f"Error searching documents with scores: {str(e)}")
            return []
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the Pinecone index."""
        try:
            index = self.pc.Index(self.index_name)
            stats = index.describe_index_stats()
            return {
                "total_vector_count": stats.total_vector_count,
                "dimension": stats.dimension,
                "index_fullness": stats.index_fullness,
                "namespaces": stats.namespaces
            }
        except Exception as e:
            logger.error(f"Error getting index stats: {str(e)}")
            return {}
    
    def delete_index(self) -> bool:
        """Delete the Pinecone index."""
        try:
            self.pc.delete_index(self.index_name)
            logger.info(f"Index '{self.index_name}' deleted successfully")
            return True
        except Exception as e:
            logger.error(f"Error deleting index: {str(e)}")
            return False
    
    def setup_complete_vector_store(self, docs_directory: str = "agents/docs") -> bool:
        """Complete setup: create index, initialize store, and populate with documents."""
        try:
            # Step 1: Create index
            if not self.create_index():
                return False
            
            # Step 2: Initialize vector store
            if not self.initialize_vector_store():
                return False
            
            # Step 3: Populate with documents
            if not self.populate_vector_store(docs_directory):
                return False
            
            logger.info("Complete vector store setup successful")
            return True
            
        except Exception as e:
            logger.error(f"Error in complete setup: {str(e)}")
            return False

# Example usage
if __name__ == "__main__":
    # Note: This only requires PINECONE_API_KEY (no Google AI key needed!)
    manager = VectorStoreManagerHF()
    
    # Setup complete vector store
    success = manager.setup_complete_vector_store()
    
    if success:
        print("Vector store setup completed successfully!")
        
        # Get stats
        stats = manager.get_index_stats()
        print(f"Index stats: {stats}")
        
        # Test search
        test_query = "leave policy"
        results = manager.search_documents(test_query, k=3)
        print(f"\nSearch results for '{test_query}':")
        for i, doc in enumerate(results):
            print(f"{i+1}. {doc.metadata.get('filename', 'Unknown')}")
            print(f"   Content preview: {doc.page_content[:100]}...")
            print()
    else:
        print("Vector store setup failed!")
