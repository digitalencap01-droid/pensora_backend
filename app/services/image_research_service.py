import asyncio
import json

from app.db.models import (
    ImageBatch,
    UploadedImageRecord,
)
from app.prompts.image import IMAGE_SYNTHESIS_PROMPT
from app.schemas.image_upload import (
    ImageAnalysisAI,
    ImageResearchRequest,
)
from app.schemas.research import (
    ResearchFact,
    ResearchResult,
    ResearchSource,
    ResearchSynthesis,
)
from app.services.image_vision_service import (
    image_vision_service,
)
from app.services.openai_service import openai_service


class ImageResearchService:
    def __init__(self) -> None:
        self.client = openai_service.client
        self.model = openai_service.model

    async def research(
        self,
        batch: ImageBatch,
        images: list[UploadedImageRecord],
        request: ImageResearchRequest,
    ) -> ResearchResult:
        # Vision calls are independent OpenAI requests, safe to run
        # concurrently.
        analyses = await asyncio.gather(
            *[
                image_vision_service.analyze_image(
                    image_url=image.public_url,
                    topic=request.topic,
                    language=request.language,
                )
                for image in images
            ]
        )

        sources = [
            ResearchSource(
                title=(
                    analysis.suggested_caption
                    or f"Image {index + 1}"
                ),
                url=image.public_url,
                domain="uploaded-images",
            )
            for index, (image, analysis) in enumerate(
                zip(images, analyses, strict=True)
            )
        ]

        key_facts = [
            ResearchFact(
                claim=detail,
                source_urls=[image.public_url],
            )
            for image, analysis in zip(
                images, analyses, strict=True
            )
            for detail in analysis.notable_details
        ]

        synthesis = await self._synthesize(
            request=request,
            images=images,
            analyses=analyses,
        )

        return ResearchResult(
            topic=request.topic,
            search_intent=synthesis.search_intent,
            summary=synthesis.summary,
            queries_used=[
                analysis.suggested_caption
                for analysis in analyses
            ],
            questions_to_answer=(
                synthesis.questions_to_answer
            ),
            key_facts=key_facts,
            statistics=[],
            recent_developments=[],
            important_entities=(
                synthesis.important_entities
            ),
            controversies_or_uncertainties=[],
            content_gaps=synthesis.content_gaps,
            article_angles=synthesis.article_angles,
            sources=sources,
        )

    async def _synthesize(
        self,
        request: ImageResearchRequest,
        images: list[UploadedImageRecord],
        analyses: list[ImageAnalysisAI],
    ) -> ResearchSynthesis:
        payload = {
            "topic": request.topic,
            "images": [
                {
                    "source_url": image.public_url,
                    "description": analysis.description,
                    "notable_details": (
                        analysis.notable_details
                    ),
                    "caption": (
                        analysis.suggested_caption
                    ),
                }
                for image, analysis in zip(
                    images, analyses, strict=True
                )
            ],
        }

        response = await self.client.responses.parse(
            model=self.model,
            instructions=IMAGE_SYNTHESIS_PROMPT,
            input=json.dumps(
                payload,
                ensure_ascii=False,
            ),
            text_format=ResearchSynthesis,
            store=False,
        )

        if response.output_parsed is None:
            raise ValueError(
                "OpenAI did not return a valid image "
                "synthesis."
            )

        return response.output_parsed


image_research_service = ImageResearchService()
