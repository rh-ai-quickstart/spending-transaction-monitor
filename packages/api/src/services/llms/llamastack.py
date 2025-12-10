import logging

import httpx
from llama_stack_client import LlamaStackClient

from core.config import settings

async_client = httpx.AsyncClient(verify=False)
http_client = httpx.Client(verify=False)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LlamastackClient:
    """
    A client for making authenticated requests to a Llama Stack instance.
    """

    def __init__(
        self, max_tokens: int = 8192, temperature: float = 0.1, top_p: float = 1
    ):
        self.client = LlamaStackClient(base_url=settings.LLAMASTACK_BASE_URL)

    def invoke(self, prompt: str) -> dict:
        try:
            response = self.client.chat.completions.create(
                messages=[{'role': 'user', 'content': prompt}],
                model=settings.LLAMASTACK_MODEL,
            )
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f'Error making LlamaStack API call: {e}')
            raise
