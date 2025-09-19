-- Enable pgvector extension
-- This script runs automatically when the PostgreSQL container starts for the first time

-- Create the vector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Grant usage on the extension to the application user
GRANT USAGE ON SCHEMA public TO "user";

-- Verify the extension is installed
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
        RAISE NOTICE 'pgvector extension successfully installed';
    ELSE
        RAISE EXCEPTION 'Failed to install pgvector extension';
    END IF;
END
$$;

-- Optional: Create a simple test to verify vector operations work
-- You can remove this section if not needed
DO $$
BEGIN
    -- Test vector creation and similarity search
    DROP TABLE IF EXISTS vector_test;
    CREATE TEMP TABLE vector_test (
        id serial PRIMARY KEY,
        embedding vector(3)
    );
    
    -- Insert test vectors
    INSERT INTO vector_test (embedding) VALUES 
        ('[1,2,3]'),
        ('[4,5,6]'),
        ('[7,8,9]');
    
    -- Test similarity search (this should work without error)
    PERFORM embedding <-> '[1,2,3]' as distance FROM vector_test LIMIT 1;
    
    RAISE NOTICE 'pgvector functionality test passed';
    
    DROP TABLE vector_test;
EXCEPTION
    WHEN OTHERS THEN
        RAISE EXCEPTION 'pgvector functionality test failed: %', SQLERRM;
END
$$;
