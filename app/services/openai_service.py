from openai import AsyncOpenAI

from app.core.config import settings


class OpenAIService:
    def __init__(self) -> None:
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key.get_secret_value(),
            # The SDK already retries connection errors, timeouts,
            # 429s, and 5xxs with exponential backoff — this just
            # makes that more resilient than the default of 2, so a
            # transient hiccup doesn't fail an entire 6-stage pipeline
            # run (and waste the tokens already spent on earlier
            # stages) over one bad request.
            max_retries=5,
            timeout=120.0,
        )
        self.model = settings.openai_model


openai_service = OpenAIService()
