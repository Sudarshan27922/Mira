import os
from dotenv import load_dotenv
from typing import Optional

# Load environment variables
load_dotenv()

class PineconeConfig:
    """Configuration class for Pinecone vector database."""
    
    def __init__(self):
        self.api_key: str = os.getenv("PINECONE_API_KEY", "")
        self.environment: str = os.getenv("PINECONE_ENVIRONMENT", "gcp-starter")  # Default to gcp-starter
        self.index_name: str = os.getenv("PINECONE_INDEX_NAME", "mira-policy-documents")
        self.dimension: int = int(os.getenv("PINECONE_DIMENSION", "768"))  # Default for text-embedding-ada-002
        self.metric: str = os.getenv("PINECONE_METRIC", "cosine")
        
    def validate(self) -> bool:
        """Validate that required configuration is present."""
        if not self.api_key:
            raise ValueError("PINECONE_API_KEY environment variable is required")
        return True
    
    def get_connection_params(self) -> dict:
        """Get connection parameters for Pinecone."""
        return {
            "api_key": self.api_key,
            "environment": self.environment
        }

# Global config instance
pinecone_config = PineconeConfig()
