#!/usr/bin/env python3
"""
Embedding Population Script
Generates OpenAI embeddings for canonical categories and populates the database.
"""

import asyncio
import os
from typing import List
from openai import OpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from db import get_db
from db.models import MerchantCategoryEmbedding


# Initialize OpenAI client
client = OpenAI()

# Canonical categories (matching updated seed_category_data.py from real CSV data)
CANONICAL_CATEGORIES = [
    "dining",
    "grocery", 
    "retail",
    "entertainment",
    "fuel",
    "health_fitness",
    "personal_care",
    "travel",
    "home",
    "kids_pets",
    "misc_net",
    "misc_pos"
]


async def clear_existing_embeddings(session: AsyncSession) -> None:
    """Clear existing embeddings for fresh population"""
    print("🧹 Clearing existing embeddings...")
    await session.execute(delete(MerchantCategoryEmbedding))
    await session.commit()
    print("✅ Cleared existing embeddings")


def generate_embedding(text: str) -> List[float]:
    """Generate OpenAI embedding for a text"""
    try:
        response = client.embeddings.create(
            input=text,
            model="text-embedding-3-small"
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"❌ Error generating embedding for '{text}': {e}")
        raise


async def populate_category_embeddings(session: AsyncSession) -> None:
    """Generate and store embeddings for all canonical categories"""
    print("🤖 Generating OpenAI embeddings for canonical categories...")
    
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ Error: OPENAI_API_KEY environment variable not set")
        print("   Please set your OpenAI API key to continue")
        return
    
    successful_embeddings = 0
    
    for i, category in enumerate(CANONICAL_CATEGORIES, 1):
        print(f"  [{i}/{len(CANONICAL_CATEGORIES)}] Generating embedding for '{category}'...")
        
        try:
            # Generate embedding for the canonical category name
            embedding = generate_embedding(category)
            
            # Store in database
            embedding_obj = MerchantCategoryEmbedding(
                category=category,
                embedding=embedding
            )
            session.add(embedding_obj)
            successful_embeddings += 1
            
            print(f"    ✅ Generated {len(embedding)} dimensional embedding")
            
        except Exception as e:
            print(f"    ❌ Failed to generate embedding for '{category}': {e}")
            continue
    
    # Commit all embeddings
    await session.commit()
    print(f"✅ Successfully generated {successful_embeddings}/{len(CANONICAL_CATEGORIES)} embeddings")


async def validate_embeddings(session: AsyncSession) -> None:
    """Validate that embeddings were stored correctly"""
    print("🔍 Validating stored embeddings...")
    
    result = await session.execute(select(MerchantCategoryEmbedding))
    embeddings = result.scalars().all()
    
    print(f"✅ Found {len(embeddings)} embeddings in database")
    
    # Validate embedding dimensions
    for embedding_obj in embeddings:
        if len(embedding_obj.embedding) != 1536:
            print(f"❌ Invalid embedding dimension for '{embedding_obj.category}': {len(embedding_obj.embedding)}")
        else:
            print(f"✅ '{embedding_obj.category}' embedding: {len(embedding_obj.embedding)} dimensions ✓")


async def test_semantic_search(session: AsyncSession) -> None:
    """Test semantic search functionality"""
    print("🧪 Testing semantic search...")
    
    test_queries = [
        "food",
        "restaurant", 
        "gas station",
        "hotel",
        "computer",
        "netflix"
    ]
    
    for query in test_queries:
        try:
            # Generate embedding for test query
            query_embedding = generate_embedding(query)
            
            # Find most similar category
            result = await session.execute(f"""
                SELECT category, embedding <-> %s as distance
                FROM merchant_category_embeddings
                ORDER BY embedding <-> %s
                LIMIT 1
            """, (query_embedding, query_embedding))
            
            row = result.fetchone()
            if row:
                category, distance = row
                print(f"  '{query}' → '{category}' (distance: {distance:.4f})")
            else:
                print(f"  '{query}' → No match found")
                
        except Exception as e:
            print(f"  '{query}' → Error: {e}")


async def main():
    """Main embedding population function"""
    print("🚀 Starting Embedding Population...")
    print(f"📊 Will generate embeddings for {len(CANONICAL_CATEGORIES)} categories")
    print(f"🤖 Using OpenAI text-embedding-3-small (1536 dimensions)")
    
    # Validate OpenAI API key
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ Error: OPENAI_API_KEY environment variable not set")
        print("   Please set your OpenAI API key:")
        print("   export OPENAI_API_KEY='your-api-key-here'")
        return 1
    
    # Get async database session  
    db_gen = get_db()
    session = await db_gen.__anext__()
    
    try:
        await clear_existing_embeddings(session)
        await populate_category_embeddings(session)
        await validate_embeddings(session)
        
        # Optional: Test semantic search if all embeddings were successful
        result = await session.execute(select(MerchantCategoryEmbedding))
        if len(result.scalars().all()) == len(CANONICAL_CATEGORIES):
            await test_semantic_search(session)
    finally:
        await session.close()
    
    print("🎉 Embedding population completed successfully!")
    print()
    print("📋 Categories with Embeddings:")
    for category in sorted(CANONICAL_CATEGORIES):
        print(f"  • {category}")
    print()
    print("🔗 Next steps:")
    print("  1. Test CategoryNormalizer service")
    print("  2. Integrate with transaction creation pipeline")
    print("  3. Update query endpoints for semantic search")


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    if exit_code:
        exit(exit_code)
