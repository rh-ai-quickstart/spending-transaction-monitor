#!/usr/bin/env python3
"""
Enable pgvector extension in the database
"""

import asyncio
from sqlalchemy import text
from db import get_db


async def enable_pgvector():
    """Enable pgvector extension"""
    print("🔌 Enabling pgvector extension...")
    
    # Get async database session  
    db_gen = get_db()
    session = await db_gen.__anext__()
    
    try:
        # Enable pgvector extension
        print("  Creating vector extension...")
        await session.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        
        # Grant usage
        print("  Granting usage permissions...")
        await session.execute('GRANT USAGE ON SCHEMA public TO "user";')
        
        # Verify installation
        print("  Verifying extension...")
        result = await session.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
        if result.scalar():
            print("  ✅ pgvector extension successfully installed")
        else:
            print("  ❌ Failed to install pgvector extension")
            return False
            
        # Test vector functionality
        print("  Testing vector functionality...")
        await session.execute("DROP TABLE IF EXISTS vector_test")
        await session.execute("CREATE TEMP TABLE vector_test (id serial PRIMARY KEY, embedding vector(3))")
        await session.execute("INSERT INTO vector_test (embedding) VALUES ('[1,2,3]'), ('[4,5,6]')")
        await session.execute("SELECT embedding <-> '[1,2,3]' as distance FROM vector_test LIMIT 1")
        print("  ✅ pgvector functionality test passed")
        
        await session.commit()
        return True
        
    except Exception as e:
        print(f"  ❌ Error enabling pgvector: {e}")
        await session.rollback()
        return False
    finally:
        await session.close()


if __name__ == "__main__":
    success = asyncio.run(enable_pgvector())
    if success:
        print("\n🎉 pgvector extension ready!")
        print("Now you can run: pnpm upgrade")
    else:
        print("\n❌ Failed to enable pgvector")
        exit(1)
