from langchain_core.tools import tool
from typing import List, Dict, Any
import logging

from ..utils.vector_store_manager import VectorStoreManager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global vector store manager instance
_vector_store_manager = None

def get_vector_store_manager() -> VectorStoreManager:
    """Get or create the global vector store manager instance."""
    global _vector_store_manager
    if _vector_store_manager is None:
        _vector_store_manager = VectorStoreManager()
        # Initialize the vector store
        if not _vector_store_manager.initialize_vector_store():
            logger.error("Failed to initialize vector store")
    return _vector_store_manager

@tool
def search_policy_documents(query: str) -> str:
    """
    Search through company policy documents to find relevant information using Hugging Face embeddings.
    
    Args:
        query: The search query to find relevant policy information
        
    Returns:
        A formatted string containing relevant policy information and sources
    """
    try:
        manager = get_vector_store_manager()
        
        # Search for relevant documents
        results = manager.search_documents(query, k=5)
        
        if not results:
            return "No relevant policy documents found for your query."
        
        # Format the results
        response = f"Found {len(results)} relevant policy documents:\n\n"
        
        for i, doc in enumerate(results, 1):
            filename = doc.metadata.get('filename', 'Unknown Document')
            chunk_index = doc.metadata.get('chunk_index', 0)
            total_chunks = doc.metadata.get('total_chunks', 1)
            
            response += f"{i}. **{filename}** (Part {chunk_index + 1} of {total_chunks})\n"
            response += f"   {doc.page_content}\n\n"
        
        return response
        
    except Exception as e:
        logger.error(f"Error searching policy documents: {str(e)}")
        return f"Error searching policy documents: {str(e)}"

@tool
def get_policy_summary(topic: str) -> str:
    """
    Get a comprehensive summary of policies related to a specific topic using Hugging Face embeddings.
    
    Args:
        topic: The policy topic to summarize (e.g., 'leave', 'disciplinary', 'harassment')
        
    Returns:
        A comprehensive summary of relevant policies
    """
    try:
        manager = get_vector_store_manager()
        
        # Search for documents related to the topic
        results = manager.search_documents(topic, k=10)
        
        if not results:
            return f"No policies found related to '{topic}'."
        
        # Group results by filename
        policy_groups = {}
        for doc in results:
            filename = doc.metadata.get('filename', 'Unknown')
            if filename not in policy_groups:
                policy_groups[filename] = []
            policy_groups[filename].append(doc)
        
        # Create summary
        response = f"Policy Summary for '{topic}':\n\n"
        
        for filename, docs in policy_groups.items():
            response += f"## {filename}\n"
            response += f"Found {len(docs)} relevant sections:\n\n"
            
            for i, doc in enumerate(docs, 1):
                response += f"**Section {i}:**\n"
                response += f"{doc.page_content}\n\n"
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting policy summary: {str(e)}")
        return f"Error getting policy summary: {str(e)}"

@tool
def find_specific_policy(policy_name: str) -> str:
    """
    Find a specific policy document by name or partial name using Hugging Face embeddings.
    
    Args:
        policy_name: The name or partial name of the policy to find
        
    Returns:
        Information about the found policy document
    """
    try:
        manager = get_vector_store_manager()
        
        # Search for the specific policy
        results = manager.search_documents(policy_name, k=10)
        
        if not results:
            return f"No policy found matching '{policy_name}'."
        
        # Filter results that match the policy name more closely
        matching_docs = []
        for doc in results:
            filename = doc.metadata.get('filename', '').lower()
            if policy_name.lower() in filename:
                matching_docs.append(doc)
        
        if not matching_docs:
            return f"No policy found with name containing '{policy_name}'."
        
        # Format the results
        response = f"Found policy document(s) matching '{policy_name}':\n\n"
        
        for i, doc in enumerate(matching_docs, 1):
            filename = doc.metadata.get('filename', 'Unknown')
            chunk_index = doc.metadata.get('chunk_index', 0)
            total_chunks = doc.metadata.get('total_chunks', 1)
            
            response += f"{i}. **{filename}** (Part {chunk_index + 1} of {total_chunks})\n"
            response += f"   {doc.page_content}\n\n"
        
        return response
        
    except Exception as e:
        logger.error(f"Error finding specific policy: {str(e)}")
        return f"Error finding specific policy: {str(e)}"

# List of RAG tools
RAG_TOOLS = [search_policy_documents, get_policy_summary, find_specific_policy]
