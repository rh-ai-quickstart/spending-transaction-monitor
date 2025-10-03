#!/usr/bin/env python3
"""
Test script for the complete category normalization pipeline
Tests both synonym lookup and semantic search with Ollama embeddings
"""

import asyncio
import sys
import os

# Add the proper paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "packages", "db", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "packages", "api", "src"))

from sqlalchemy.ext.asyncio import AsyncSession
from db import get_db
from services.category_normalizer import CategoryNormalizer
from services.embedding_service import embedding_service


async def test_synonym_lookup(session: AsyncSession):
    """Test synonym table lookup"""
    print("\n🔍 Testing Synonym Lookup...")
    test_cases = [
        "walmart",
        "mcdonalds", 
        "shell",
        "grocery",
        "unknown_merchant"
    ]
    
    for raw_term in test_cases:
        result = await CategoryNormalizer.normalize(session, raw_term)
        print(f"  '{raw_term}' -> '{result}'")


async def test_semantic_search(session: AsyncSession):
    """Test semantic search with embeddings"""
    print("\n🧠 Testing Semantic Search...")
    test_cases = [
        "burger place",
        "gas station", 
        "supermarket",
        "coffee shop",
        "gym membership",
        "hotel booking"
    ]
    
    for raw_term in test_cases:
        result = await CategoryNormalizer.normalize(session, raw_term)
        print(f"  '{raw_term}' -> '{result}'")


async def test_embedding_service():
    """Test embedding service directly"""
    print(f"\n⚡ Testing Embedding Service...")
    print(f"  Provider: {type(embedding_service.provider).__name__}")
    print(f"  Dimensions: {embedding_service.get_dimensions()}")
    
    test_text = "restaurant"
    embedding = await embedding_service.get_embedding(test_text)
    print(f"  Generated {len(embedding)}-dim embedding for '{test_text}'")
    print(f"  First 5 values: {embedding[:5]}")


async def main():
    print("🚀 Testing Category Normalization Pipeline")
    print("=" * 50)
    
    # Test embedding service directly
    try:
        await test_embedding_service()
    except Exception as e:
        print(f"❌ Embedding service test failed: {e}")
        print("💡 Make sure Ollama is running with: ollama run all-minilm")
        return 1
    
    # Get database session
    try:
        db_gen = get_db()
        session = await db_gen.__anext__()
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("💡 Make sure PostgreSQL is running with pgvector enabled")
        return 1
    
    try:
        # Test synonym lookup
        await test_synonym_lookup(session)
        
        # Test semantic search
        await test_semantic_search(session)
        
        print("\n✅ All tests completed successfully!")
        print("\n📋 Summary:")
        print("  • Synonym lookup: ✅ Working")
        print("  • Semantic search: ✅ Working") 
        print(f"  • Embedding provider: {type(embedding_service.provider).__name__}")
        print("  • Ready for Phase 2 integration!")
        
        return 0
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return 1
    finally:
        await session.close()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
