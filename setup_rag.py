#!/usr/bin/env python3
"""
Simple setup script for Mira RAG system.
This script sets up the Pinecone vector store with Hugging Face embeddings.
"""

import os
import sys
import time
import argparse
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from agents.utils.vector_store_manager import VectorStoreManager
from dotenv import load_dotenv

def main():
    """Main setup function."""
    print("🚀 Setting up Mira RAG System")
    print("=" * 50)
    print("✅ Using FREE Hugging Face embeddings")
    print("=" * 50)
    
    # Load environment variables
    load_dotenv()
    
    # Check for required environment variables
    if not os.getenv("PINECONE_API_KEY"):
        print("❌ Missing PINECONE_API_KEY environment variable")
        print("Please set PINECONE_API_KEY in your .env file")
        return False
    
    try:
        parser = argparse.ArgumentParser(description="Setup Pinecone vector store for Mira RAG")
        parser.add_argument("--it-docs", action="store_true", help="Ingest IT guides from repo 'docs/' into namespace 'it'")
        parser.add_argument("--docs-dir", type=str, default=None, help="Custom documents directory to ingest")
        parser.add_argument("--namespace", type=str, default=None, help="Namespace to bind during ingestion/search")
        parser.add_argument("--category", type=str, default=None, help="Category metadata to tag during ingestion")
        parser.add_argument("--no-interactive", action="store_true", help="Disable interactive prompts (non-destructive)")
        args = parser.parse_args()

        # Initialize vector store manager
        print("📋 Initializing vector store manager...")
        manager = VectorStoreManager()
        
        # Check if index already exists and ask user what to do (unless non-interactive)
        existing_indexes = [index.name for index in manager.pc.list_indexes()]
        if manager.index_name in existing_indexes and not args.no_interactive:
            print(f"⚠️  Index '{manager.index_name}' already exists")
            response = input("Do you want to delete and recreate it? (y/N): ").strip().lower()
            
            if response in ['y', 'yes']:
                print("🗑️  Deleting existing index...")
                manager.delete_index()
                print("⏳ Waiting for deletion to complete...")
                time.sleep(5)
            else:
                print("ℹ️  Using existing index")
        
        # Determine ingestion parameters
        docs_dir = args.docs_dir
        namespace = args.namespace
        category = args.category

        if args.it_docs:
            # IT ingestion defaults
            docs_dir = docs_dir or "docs"
            namespace = namespace or "it"
            category = category or "it"

        # Setup complete vector store
        print("\n🔧 Setting up vector store...")
        success = manager.setup_complete_vector_store(
            docs_directory=docs_dir or "agents/docs",
            category=category,
            namespace=namespace,
        )
        
        if success:
            print("✅ Vector store setup completed successfully!")
            
            # Get and display stats
            print("\n📊 Vector Store Statistics:")
            stats = manager.get_index_stats()
            print(f"   - Total vectors: {stats.get('total_vector_count', 'Unknown')}")
            print(f"   - Dimension: {stats.get('dimension', 'Unknown')}")
            print(f"   - Index fullness: {stats.get('index_fullness', 'Unknown')}")
            
            # Test search functionality
            print("\n🔍 Testing search functionality...")
            test_query = "leave policy" if namespace is None else "password reset"
            results = manager.search_documents(test_query, k=3, namespace=namespace, category=category)
            
            if results:
                print(f"   ✅ Found {len(results)} results for '{test_query}'")
                for i, doc in enumerate(results, 1):
                    filename = doc.metadata.get('filename', 'Unknown')
                    print(f"      {i}. {filename}")
            else:
                print("   ⚠️  No results found for test query")
            
            print("\n🎉 Setup complete! You can now use Mira with RAG capabilities.")
            print("\n💡 Test it with:")
            print('   python -c "from agents.mira.mira import main_agent; print(main_agent(\'What is the leave policy?\'))"')
            
            return True
        else:
            print("❌ Vector store setup failed!")
            return False
            
    except Exception as e:
        print(f"❌ Error during setup: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
