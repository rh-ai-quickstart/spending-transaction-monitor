import logging

import httpx
from langchain_openai import ChatOpenAI

from core.config import settings

async_client = httpx.AsyncClient(verify=False)
http_client = httpx.Client(verify=False)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMClient:
    """
    A client for making authenticated requests to different LLM Servers
    that support OpenAI API.
    """

    def __init__(
        self, max_tokens: int = 8192, temperature: float = 0.1, top_p: float = 1
    ):
        logger.info(
            'LLM client (OpenAI-compatible): base_url=%s model=%s',
            settings.BASE_URL or '(default)',
            settings.MODEL,
        )
        self.llm = ChatOpenAI(
            api_key=settings.API_KEY,
            model=settings.MODEL,
            base_url=settings.BASE_URL,
            async_client=async_client,
            http_client=http_client,
            max_tokens=max_tokens,
            top_p=top_p,
            temperature=temperature,
        )

    def invoke(self, prompt: str) -> dict:
        try:
            response = self.llm.invoke(prompt)
            content = response.content

            logger.info(f'AI response: {content}')
            return content

        except Exception as e:
            logger.error(f'Error making LLM AI API call: {e}')
            raise
