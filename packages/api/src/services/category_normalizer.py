# category_normalizer.py

import logging

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import MerchantCategorySynonym

from .embedding_service import embedding_service

logger = logging.getLogger(__name__)


class CategoryNormalizer:
    @staticmethod
    async def normalize(session: AsyncSession, raw_term: str) -> str:
        raw_lower = raw_term.lower()

        # 1. Try Synonym Table
        result = await session.execute(
            select(MerchantCategorySynonym.canonical_category).where(
                MerchantCategorySynonym.synonym == raw_lower
            )
        )
        synonym_match = result.scalar()
        if synonym_match:
            return synonym_match

        # 2. Fall back to embeddings
        try:
            emb = await embedding_service.get_embedding(raw_lower)
            logger.info(f"Generated {len(emb)}-dim embedding for '{raw_lower}'")

            # Use direct string formatting for pgvector compatibility (same as populate script)
            vector_str = '[' + ','.join(map(str, emb)) + ']'

            result = await session.execute(
                text(f"""
                    SELECT category
                    FROM merchant_category_embeddings
                    ORDER BY embedding <-> '{vector_str}'::vector
                    LIMIT 1
                """)
            )
        except Exception as e:
            logger.error(f"Error generating embedding for '{raw_lower}': {e}")
            # Fall back to raw term if embedding fails
            return raw_lower
        embedding_match = result.scalar()
        if embedding_match:
            return embedding_match

        # 3. Default: return raw
        return raw_lower
