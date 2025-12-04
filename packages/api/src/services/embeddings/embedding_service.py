"""
Embedding Service - Provides a unified interface for different embedding providers
Follows the same pattern as LLM service in the llamastack implementation
"""

from abc import ABC, abstractmethod
import logging
import os

import httpx
from openai import OpenAI

from core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers"""

    @abstractmethod
    async def get_embedding(self, text: str) -> list[float]:
        """Generate embedding for the given text"""
        pass

    @abstractmethod
    def get_dimensions(self) -> int:
        """Return the dimensionality of embeddings from this provider"""
        pass


class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    """
    Local sentence-transformers embedding provider - no external dependencies.
    Runs the all-MiniLM model directly within the application using Hugging Face transformers.
    """

    def __init__(self):
        try:
            from sentence_transformers import SentenceTransformer

            self._SentenceTransformer = SentenceTransformer
        except ImportError as e:
            raise ImportError(
                'sentence-transformers is required for local embedding generation. '
                'Install it with: pip install sentence-transformers'
            ) from e

        self.model_name = settings.EMBEDDING_MODEL
        self.dimensions = settings.EMBEDDING_DIMENSIONS

        # Map common model names to sentence-transformers format
        model_mapping = {
            'all-minilm': 'sentence-transformers/all-MiniLM-L6-v2',
            'all-MiniLM-L6-v2': 'sentence-transformers/all-MiniLM-L6-v2',
            'all-minilm-l6-v2': 'sentence-transformers/all-MiniLM-L6-v2',
        }

        self.model_identifier = model_mapping.get(self.model_name, self.model_name)

        logger.info(f'Loading sentence-transformers model: {self.model_identifier}')
        try:
            self.model = self._SentenceTransformer(self.model_identifier)
            logger.info(f'Successfully loaded model with {self.dimensions} dimensions')
        except Exception as e:
            logger.error(f'Failed to load sentence-transformers model: {e}')
            raise

    async def get_embedding(self, text: str) -> list[float]:
        """
        Generate embedding using local sentence-transformers model.
        This runs entirely locally without any external service dependencies.
        """
        try:
            # sentence-transformers encode is synchronous, but we wrap it in async context
            # For true async, we could use asyncio.to_thread in Python 3.9+
            embedding = self.model.encode(text.lower(), convert_to_tensor=False)

            # Convert numpy array to list
            embedding_list = embedding.tolist()

            if len(embedding_list) != self.dimensions:
                raise ValueError(
                    f'Expected {self.dimensions} dimensions, got {len(embedding_list)}'
                )

            logger.info(
                f'Generated {len(embedding_list)}-dim embedding locally (sentence-transformers)'
            )
            return embedding_list

        except Exception as e:
            logger.error(f'Error generating local embedding: {e}')
            raise

    def get_dimensions(self) -> int:
        return self.dimensions


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI embedding provider"""

    def __init__(self):
        self.client = OpenAI(api_key=settings.API_KEY, base_url=settings.BASE_URL)
        self.model = settings.EMBEDDING_MODEL
        self.dimensions = settings.EMBEDDING_DIMENSIONS

    async def get_embedding(self, text: str) -> list[float]:
        try:
            response = self.client.embeddings.create(
                input=text.lower(), model=self.model
            )
            embedding = response.data[0].embedding
            logger.info(f'Generated {len(embedding)}-dim embedding via OpenAI')
            return embedding
        except Exception as e:
            logger.error(f'Error generating OpenAI embedding: {e}')
            raise

    def get_dimensions(self) -> int:
        return self.dimensions


class OllamaEmbeddingProvider(EmbeddingProvider):
    """Ollama embedding provider - local, fast, no API costs"""

    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.EMBEDDING_MODEL
        self.dimensions = settings.EMBEDDING_DIMENSIONS

    async def get_embedding(self, text: str) -> list[float]:
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f'{self.base_url}/api/embeddings',
                    json={'model': self.model, 'prompt': text.lower()},
                )
                response.raise_for_status()
                result = response.json()

                embedding = result.get('embedding', [])
                if len(embedding) != self.dimensions:
                    raise ValueError(
                        f'Expected {self.dimensions} dimensions, got {len(embedding)}'
                    )

                logger.info(f'Generated {len(embedding)}-dim embedding via Ollama')
                return embedding

        except Exception as e:
            logger.error(f'Error generating Ollama embedding: {e}')
            raise

    def get_dimensions(self) -> int:
        return self.dimensions


class LlamaStackEmbeddingProvider(EmbeddingProvider):
    """LlamaStack embedding provider - for future implementation"""

    def __init__(self):
        self.base_url = settings.LLAMASTACK_BASE_URL
        self.model = settings.EMBEDDING_MODEL
        self.dimensions = settings.EMBEDDING_DIMENSIONS

    async def get_embedding(self, text: str) -> list[float]:
        """
        TODO: Implement LlamaStack embedding API calls
        This will be implemented when the LlamaStack PR merges
        """
        try:
            # Future LlamaStack API implementation
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f'{self.base_url}/embeddings',  # TBD: actual endpoint
                    json={'model': self.model, 'input': text.lower()},
                )
                response.raise_for_status()
                result = response.json()

                embedding = result.get('embedding', [])
                logger.info(f'Generated {len(embedding)}-dim embedding via LlamaStack')
                return embedding

        except Exception as e:
            logger.error(f'Error generating LlamaStack embedding: {e}')
            raise

    def get_dimensions(self) -> int:
        return self.dimensions


def get_embedding_client() -> EmbeddingProvider:
    """
    Factory function to get the appropriate embedding provider
    Follows the same pattern as get_llm_client() in the llamastack implementation

    Default: 'local' - Uses sentence-transformers for local, self-contained embeddings
    """
    provider = os.getenv('EMBEDDING_PROVIDER', settings.EMBEDDING_PROVIDER)

    if provider == 'local' or provider == 'sentence-transformers':
        return SentenceTransformerEmbeddingProvider()
    elif provider == 'ollama':
        logger.warning(
            "Ollama provider is deprecated. Consider using 'local' provider instead."
        )
        return OllamaEmbeddingProvider()
    elif provider == 'llamastack':
        return LlamaStackEmbeddingProvider()
    elif provider == 'openai':
        return OpenAIEmbeddingProvider()
    else:
        logger.warning(
            f'Unknown embedding provider: {provider}, defaulting to local sentence-transformers'
        )
        return SentenceTransformerEmbeddingProvider()


class EmbeddingService:
    """
    Main embedding service that uses the configured provider
    This provides a consistent interface regardless of underlying provider
    """

    def __init__(self):
        self.provider = get_embedding_client()
        logger.info(
            f'Initialized embedding service with provider: {type(self.provider).__name__}'
        )

    async def get_embedding(self, text: str) -> list[float]:
        """Generate embedding for text using configured provider"""
        return await self.provider.get_embedding(text)

    def get_dimensions(self) -> int:
        """Get embedding dimensions from current provider"""
        return self.provider.get_dimensions()


# Global embedding service instance
embedding_service = EmbeddingService()
