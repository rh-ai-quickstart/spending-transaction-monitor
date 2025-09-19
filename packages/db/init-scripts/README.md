# PostgreSQL Initialization Scripts

This directory contains SQL scripts that are executed automatically when the PostgreSQL container starts for the first time.

## Scripts

### 01-enable-pgvector.sql
Enables the pgvector extension which provides:
- Vector data type for storing embeddings
- Similarity search operators (`<->`, `<#>`, `<=>`)
- Index types for efficient vector search (IVFFlat, HNSW)

## pgvector Usage Examples

### Creating a table with vector columns:
```sql
CREATE TABLE documents (
    id serial PRIMARY KEY,
    content text,
    embedding vector(1536)  -- OpenAI embedding dimension
);
```

### Inserting vector data:
```sql
INSERT INTO documents (content, embedding) 
VALUES ('Sample text', '[0.1, 0.2, 0.3, ...]');
```

### Similarity search:
```sql
-- L2 distance (Euclidean)
SELECT * FROM documents 
ORDER BY embedding <-> '[0.1, 0.2, 0.3, ...]' 
LIMIT 5;

-- Cosine distance
SELECT * FROM documents 
ORDER BY embedding <=> '[0.1, 0.2, 0.3, ...]' 
LIMIT 5;

-- Inner product
SELECT * FROM documents 
ORDER BY embedding <#> '[0.1, 0.2, 0.3, ...]' 
LIMIT 5;
```

### Creating vector indexes for performance:
```sql
-- IVFFlat index (good for L2 and inner product)
CREATE INDEX ON documents USING ivfflat (embedding vector_l2_ops);

-- HNSW index (good for L2, inner product, and cosine distance)
CREATE INDEX ON documents USING hnsw (embedding vector_l2_ops);
CREATE INDEX ON documents USING hnsw (embedding vector_cosine_ops);
```

## Notes

- The pgvector extension is automatically enabled when the container starts
- Vector dimensions must be specified when creating columns (e.g., `vector(1536)`)
- Maximum vector dimension is 16,000
- For large datasets, consider using appropriate indexes for performance
