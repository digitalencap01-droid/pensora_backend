from openai import AsyncOpenAI

from app.core.config import settings


class OpenAIService:
    def __init__(self) -> None:
        api_key = (
            settings.openai_api_key.get_secret_value()
            if settings.openai_api_key
            else ""
        )
        if not api_key:
            api_key = "dummy_key_until_configured"

        self.client = AsyncOpenAI(
            api_key=api_key,
            max_retries=5,
            timeout=120.0,
        )
        self.model = settings.openai_model


openai_service = OpenAIService()
