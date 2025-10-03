#!/usr/bin/env python3
"""
Ollama Embedding Population Script
Generates embeddings for ALL synonyms using Ollama and populates the database.

🚨 CRITICAL ARCHITECTURE FIX:
- Creates embeddings for ALL synonyms (not just canonical categories)
- Each synonym gets its own embedding mapped to its canonical category
- This enables proper semantic search for terms like "burger place" → "dining"
"""

import asyncio
from typing import List, Tuple
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, text
from db import get_db
from db.models import MerchantCategoryEmbedding, MerchantCategorySynonym


# Ollama configuration
OLLAMA_BASE_URL = "http://localhost:11434"
EMBEDDING_MODEL = "all-minilm:l6-v2"  # Specific model name for reproducibility
EXPECTED_DIMENSIONS = 384


async def check_ollama_health() -> bool:
    """Check if Ollama is running and model is available"""
    print("🔍 Checking Ollama availability...")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Check if Ollama is running
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            response.raise_for_status()
            
            models = response.json().get("models", [])
            model_names = [model["name"] for model in models]
            
            if EMBEDDING_MODEL not in model_names:
                print(f"❌ Model '{EMBEDDING_MODEL}' not found in Ollama")
                print(f"Available models: {model_names}")
                print(f"Run: ollama pull {EMBEDDING_MODEL}")
                return False
            
            print(f"✅ Ollama running with model '{EMBEDDING_MODEL}'")
            return True
            
    except Exception as e:
        print(f"❌ Ollama not available: {e}")
        print("Make sure Ollama is running: ollama serve")
        return False


async def generate_embedding_ollama(text: str) -> List[float]:
    """Generate embedding using Ollama API"""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/embeddings",
                json={
                    "model": EMBEDDING_MODEL,
                    "prompt": text.lower()  # Normalize case
                }
            )
            response.raise_for_status()
            result = response.json()
            
            embedding = result.get("embedding", [])
            if len(embedding) != EXPECTED_DIMENSIONS:
                raise ValueError(f"Expected {EXPECTED_DIMENSIONS} dimensions, got {len(embedding)}")
            
            return embedding
            
    except Exception as e:
        print(f"❌ Error generating embedding for '{text}': {e}")
        raise


async def clear_existing_embeddings(session: AsyncSession) -> None:
    """Clear existing embeddings for fresh population"""
    print("🧹 Clearing existing embeddings...")
    await session.execute(delete(MerchantCategoryEmbedding))
    await session.commit()
    print("✅ Cleared existing embeddings")


async def update_embedding_column_dimension(session: AsyncSession) -> None:
    """Dynamically update the 'embedding' column dimension if it doesn't match"""
    print(f"🔧 Ensuring embedding column is {EXPECTED_DIMENSIONS} dimensions...")
    
    try:
        # Check current column info
        result = await session.execute(text("""
            SELECT atttypmod 
            FROM pg_attribute 
            WHERE attrelid = 'merchant_category_embeddings'::regclass 
            AND attname = 'embedding'
        """))
        current_dim_info = result.scalar()
        
        if current_dim_info and current_dim_info != EXPECTED_DIMENSIONS + 4:  # pgvector adds 4 to dimension
            print(f"🔄 Updating embedding column from current to {EXPECTED_DIMENSIONS} dimensions...")
            await session.execute(text("ALTER TABLE merchant_category_embeddings DROP COLUMN embedding"))
            await session.execute(text(f"ALTER TABLE merchant_category_embeddings ADD COLUMN embedding vector({EXPECTED_DIMENSIONS})"))
            await session.commit()
            print(f"✅ Updated embedding column to {EXPECTED_DIMENSIONS} dimensions")
        else:
            print(f"✅ Embedding column already {EXPECTED_DIMENSIONS} dimensions")
            
    except Exception as e:
        print(f"⚠️  Schema update note: {e}")
        await session.rollback()


async def get_all_synonyms(session: AsyncSession) -> List[Tuple[str, str]]:
    """Fetch all synonym->canonical category mappings from database"""
    print("📊 Fetching all synonyms from database...")
    result = await session.execute(
        select(MerchantCategorySynonym.synonym, MerchantCategorySynonym.canonical_category)
        .order_by(MerchantCategorySynonym.canonical_category, MerchantCategorySynonym.synonym)
    )
    synonyms = result.fetchall()
    print(f"✅ Found {len(synonyms)} synonyms to process")
    return synonyms


async def populate_all_synonym_embeddings(session: AsyncSession) -> None:
    """
    🎯 CORE FIX: Generate embeddings for ALL synonyms, not just canonical categories
    This enables proper semantic search for ANY term in our synonym database
    """
    # Fetch all synonyms from database
    synonyms = await get_all_synonyms(session)
    
    if not synonyms:
        print("❌ No synonyms found! Run seed_category_data.py first.")
        return
    
    print(f"🤖 Generating embeddings for {len(synonyms)} synonyms using {EMBEDDING_MODEL}...")
    
    # Group by canonical category for organized logging
    by_category = {}
    for synonym, canonical in synonyms:
        if canonical not in by_category:
            by_category[canonical] = []
        by_category[canonical].append(synonym)
    
    total_processed = 0
    successful_embeddings = 0
    
    for canonical_category in sorted(by_category.keys()):
        synonym_list = by_category[canonical_category]
        print(f"\\n📂 Processing {len(synonym_list)} synonyms for '{canonical_category}':")
        
        for synonym in sorted(synonym_list):
            total_processed += 1
            print(f"  [{total_processed}/{len(synonyms)}] '{synonym}' → '{canonical_category}'...")
            
            try:
                # Generate embedding for the synonym text
                embedding = await generate_embedding_ollama(synonym)
                
                # Store in database - each synonym gets its own embedding
                # but is mapped to the canonical category for retrieval
                synonym_embedding = MerchantCategoryEmbedding(
                    category=canonical_category,  # What category this represents
                    synonym=synonym,              # Which specific synonym this is
                    embedding=embedding          # Vector for THIS specific synonym
                )
                session.add(synonym_embedding)
                successful_embeddings += 1
                
                print(f"    ✅ {len(embedding)}-dim embedding stored")
                
            except Exception as e:
                print(f"    ❌ Failed: {e}")
                continue
    
    # Commit all embeddings
    await session.commit()
    print(f"\\n🎉 Successfully generated {successful_embeddings}/{len(synonyms)} embeddings!")
    
    # Show category breakdown
    print(f"\\n📊 Embedding Breakdown by Category:")
    for category, synonym_list in sorted(by_category.items()):
        print(f"  • {category}: {len(synonym_list)} synonyms")


async def validate_embeddings(session: AsyncSession) -> None:
    """Validate that embeddings were stored correctly"""
    print("\\n🔍 Validating stored embeddings...")
    
    result = await session.execute(select(MerchantCategoryEmbedding))
    embeddings = result.scalars().all()
    
    if not embeddings:
        print("❌ No embeddings found in database!")
        return
    
    print(f"✅ Found {len(embeddings)} embeddings in database")
    
    # Group by category
    by_category = {}
    for emb in embeddings:
        if emb.category not in by_category:
            by_category[emb.category] = 0
        by_category[emb.category] += 1
    
    print(f"\\n📊 Embeddings by category:")
    for category, count in sorted(by_category.items()):
        print(f"  • {category}: {count} embeddings")
    
    # Check dimensions
    dimension_issues = []
    for emb in embeddings:
        if len(emb.embedding) != EXPECTED_DIMENSIONS:
            dimension_issues.append(f"{emb.category}: {len(emb.embedding)}")
    
    if dimension_issues:
        print(f"❌ Dimension issues found: {dimension_issues}")
    else:
        print(f"✅ All embeddings have correct {EXPECTED_DIMENSIONS} dimensions")


async def test_semantic_search(session: AsyncSession) -> None:
    """Test the new semantic search with synonym embeddings"""
    print("\\n🧪 Testing semantic search with real examples...")
    
    test_cases = [
        ("burger place", "dining"),
        ("coffee shop", "dining"), 
        ("gas station", "fuel"),
        ("walmart", "retail"),
        ("hotel booking", "travel"),
        ("supermarket", "grocery")
    ]
    
    for query_text, expected_category in test_cases:
        try:
            # Generate embedding for test query
            query_embedding = await generate_embedding_ollama(query_text)
            vector_str = '[' + ','.join(map(str, query_embedding)) + ']'
            
            # Find closest match
            result = await session.execute(text(f"""
                SELECT category
                FROM merchant_category_embeddings
                ORDER BY embedding <-> '{vector_str}'::vector
                LIMIT 1
            """))
            
            actual_category = result.scalar()
            status = "✅" if actual_category == expected_category else "❌"
            print(f"  {status} '{query_text}' → '{actual_category}' (expected: '{expected_category}')")
            
        except Exception as e:
            print(f"  ❌ '{query_text}' → ERROR: {e}")


async def main() -> int:
    """Main function to populate embeddings for all synonyms"""
    print("🚀 Ollama Synonym Embeddings Population")
    print("=" * 50)
    
    # Health checks
    if not await check_ollama_health():
        return 1
    
    # Database session
    db_gen = get_db()
    session = await db_gen.__anext__()
    
    try:
        # Execution steps
        await update_embedding_column_dimension(session)
        await clear_existing_embeddings(session)
        await populate_all_synonym_embeddings(session)
        await validate_embeddings(session)
        await test_semantic_search(session)
        
        print("\\n🎉 Synonym embeddings population completed successfully!")
        print("\\n🔗 Next steps:")
        print("  • Test category normalization: CategoryNormalizer.normalize()")
        print("  • Verify 'burger place' → 'dining' and 'coffee shop' → 'dining'")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error during execution: {e}")
        return 1
        
    finally:
        await session.close()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)