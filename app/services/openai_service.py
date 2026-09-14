import httpx
from openai import AsyncOpenAI

from app.core.config import settings


class OpenAIService:
    @property
    def client(self) -> AsyncOpenAI:
        api_key = (
            settings.openai_api_key.get_secret_value()
            if settings.openai_api_key
            else ""
        )
        if not api_key:
            api_key = "dummy_key_until_configured"
        return AsyncOpenAI(
            api_key=api_key,
            max_retries=5,
            timeout=120.0,
            http_client=httpx.AsyncClient(headers={"Accept-Encoding": "gzip, deflate"}),
        )

    @property
    def model(self) -> str:
        return settings.openai_model


openai_service = OpenAIService()
