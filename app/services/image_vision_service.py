from app.prompts.image import IMAGE_ANALYSIS_PROMPT
from app.schemas.image_upload import ImageAnalysisAI
from app.services.openai_service import openai_service


class ImageVisionService:
    def __init__(self) -> None:
        self.client = openai_service.client
        self.model = openai_service.model

    async def analyze_image(
        self,
        image_url: str,
        topic: str,
        language: str,
    ) -> ImageAnalysisAI:
        response = await self.client.responses.parse(
            model=self.model,
            instructions=IMAGE_ANALYSIS_PROMPT,
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                f"Topic: {topic}\n"
                                f"Output language: {language}"
                            ),
                        },
                        {
                            "type": "input_image",
                            "image_url": image_url,
                            "detail": "auto",
                        },
                    ],
                }
            ],
            text_format=ImageAnalysisAI,
            store=False,
        )

        analysis = response.output_parsed

        if analysis is None:
            raise ValueError(
                "OpenAI did not return a valid image "
                "analysis."
            )

        return analysis


image_vision_service = ImageVisionService()
