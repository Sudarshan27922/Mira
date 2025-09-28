#!/usr/bin/env python3
"""
Test script for Mira RAG system.
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from agents.mira.mira import main_agent

def test_queries():
    """Test various policy queries."""
    test_cases = [
        "What is the company policy on leave?",
        "What is the dress code policy?",
        "Tell me about the harassment policy",
        "What are the disciplinary procedures?",
        "Find information about flexible working"
    ]
    
    print("🧪 Testing Mira RAG System")
    print("=" * 50)
    
    for i, query in enumerate(test_cases, 1):
        print(f"\n📝 Test {i}: {query}")
        print("-" * 40)
        
        try:
            response = main_agent(query)
            print(f"✅ Response: {response[:200]}...")
        except Exception as e:
            print(f"❌ Error: {str(e)}")
    
    print("\n🎉 Testing complete!")

if __name__ == "__main__":
    test_queries()
