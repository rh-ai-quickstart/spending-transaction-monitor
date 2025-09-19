# category_normalizer.py

from openai import OpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import MerchantCategorySynonym

client = OpenAI()


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
        emb = (
            client.embeddings.create(input=raw_lower, model='text-embedding-3-small')
            .data[0]
            .embedding
        )

        result = await session.execute(
            """
            SELECT category
            FROM merchant_category_embeddings
            ORDER BY embedding <-> :vector
            LIMIT 1
            """,
            {'vector': emb},
        )
        embedding_match = result.scalar()
        if embedding_match:
            return embedding_match

        # 3. Default: return raw
        return raw_lower
