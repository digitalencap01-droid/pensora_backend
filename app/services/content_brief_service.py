import json

from app.prompts.content_brief import (
    CONTENT_BRIEF_PROMPT,
)
from app.schemas.content_brief import (
    ContentBriefAI,
    ContentBriefRequest,
    ContentBriefResult,
    OutlineSection,
)
from app.services.openai_service import (
    openai_service,
)


class ContentBriefService:
    def __init__(self) -> None:
        self.client = openai_service.client
        self.model = openai_service.model

    async def create_brief(
        self,
        request: ContentBriefRequest,
    ) -> ContentBriefResult:
        payload = self._build_payload(request)

        response = await self.client.responses.parse(
            model=self.model,
            instructions=CONTENT_BRIEF_PROMPT,
            input=json.dumps(
                payload,
                ensure_ascii=False,
            ),
            text_format=ContentBriefAI,
            store=False,
        )

        brief = response.output_parsed

        if brief is None:
            raise ValueError(
                "OpenAI did not return a valid "
                "content brief."
            )

        brief.sections = self._normalize_sections(
            sections=brief.sections,
            allowed_urls=self._allowed_source_urls(
                request
            ),
        )

        return ContentBriefResult(
            topic=request.research.topic,
            article_type=request.article_type,
            tone=request.tone,
            target_word_count=(
                request.target_word_count
            ),
            primary_keyword=(
                request
                .keywords
                .primary_keyword
                .keyword
            ),
            search_intent=(
                request
                .keywords
                .search_intent
                .primary_intent
            ),
            content_angle=brief.content_angle,
            unique_value_proposition=(
                brief.unique_value_proposition
            ),
            target_reader=brief.target_reader,
            reader_problem=brief.reader_problem,
            reader_outcome=brief.reader_outcome,
            recommended_title=(
                brief.recommended_title
            ),
            alternative_titles=(
                self._dedupe_strings(
                    brief.alternative_titles
                )
            ),
            h1=brief.h1,
            introduction_strategy=(
                brief.introduction_strategy
            ),
            sections=brief.sections,
            conclusion_strategy=(
                brief.conclusion_strategy
            ),
            cta_strategy=brief.cta_strategy,
            image_opportunities=(
                brief.image_opportunities
            ),
            internal_link_opportunities=(
                brief.internal_link_opportunities
            ),
            important_warnings=(
                self._dedupe_strings(
                    brief.important_warnings
                )
            ),
        )

    def _build_payload(
        self,
        request: ContentBriefRequest,
    ) -> dict:
        research = request.research
        keywords = request.keywords

        return {
            "topic": research.topic,
            "article_requirements": {
                "article_type": (
                    request.article_type
                ),
                "tone": request.tone,
                "target_audience": (
                    request.target_audience
                ),
                "target_word_count": (
                    request.target_word_count
                ),
                "brand_name": (
                    request.brand_name
                ),
                "call_to_action": (
                    request.call_to_action
                ),
            },
            "search_intent": (
                keywords.search_intent.model_dump()
            ),
            "primary_keyword": (
                keywords
                .primary_keyword
                .model_dump()
            ),
            "secondary_keywords": [
                keyword.model_dump()
                for keyword in (
                    keywords.secondary_keywords
                )
            ],
            "long_tail_keywords": [
                keyword.model_dump()
                for keyword in (
                    keywords.long_tail_keywords
                )
            ],
            "question_keywords": [
                keyword.model_dump()
                for keyword in (
                    keywords.question_keywords
                )
            ],
            "semantic_terms": (
                keywords.semantic_terms
            ),
            "must_cover_topics": (
                keywords.must_cover_topics
            ),
            "differentiation_opportunities": (
                keywords
                .differentiation_opportunities
            ),
            "internal_link_topics": (
                keywords.internal_link_topics
            ),
            "research_summary": (
                research.summary
            ),
            "key_facts": [
                fact.model_dump()
                for fact in research.key_facts
            ],
            "statistics": [
                fact.model_dump()
                for fact in research.statistics
            ],
            "recent_developments": [
                fact.model_dump()
                for fact in (
                    research.recent_developments
                )
            ],
            "questions_to_answer": (
                research.questions_to_answer
            ),
            "important_entities": (
                research.important_entities
            ),
            "controversies_or_uncertainties": (
                research
                .controversies_or_uncertainties
            ),
            "content_gaps": (
                research.content_gaps
            ),
            "available_sources": [
                source.model_dump()
                for source in research.sources
            ],
        }

    def _allowed_source_urls(
        self,
        request: ContentBriefRequest,
    ) -> set[str]:
        return {
            source.url
            for source in request.research.sources
        }

    def _normalize_sections(
        self,
        sections: list[OutlineSection],
        allowed_urls: set[str],
    ) -> list[OutlineSection]:
        normalized_sections = []

        for index, section in enumerate(
            sections,
            start=1,
        ):
            section.section_id = f"section-{index}"

            section.target_keywords = (
                self._dedupe_strings(
                    section.target_keywords
                )
            )

            section.semantic_terms = (
                self._dedupe_strings(
                    section.semantic_terms
                )
            )

            section.questions_answered = (
                self._dedupe_strings(
                    section.questions_answered
                )
            )

            section.key_points = (
                self._dedupe_strings(
                    section.key_points
                )
            )

            section.evidence_urls = [
                url
                for url in self._dedupe_strings(
                    section.evidence_urls
                )
                if url in allowed_urls
            ]

            for subsection in section.subsections:
                subsection.target_keywords = (
                    self._dedupe_strings(
                        subsection.target_keywords
                    )
                )

                subsection.questions_answered = (
                    self._dedupe_strings(
                        subsection.questions_answered
                    )
                )

                subsection.key_points = (
                    self._dedupe_strings(
                        subsection.key_points
                    )
                )

                subsection.evidence_urls = [
                    url
                    for url
                    in self._dedupe_strings(
                        subsection.evidence_urls
                    )
                    if url in allowed_urls
                ]

            normalized_sections.append(
                section
            )

        return normalized_sections

    def _dedupe_strings(
        self,
        values: list[str],
    ) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []

        for value in values:
            cleaned = value.strip()
            normalized = cleaned.casefold()

            if not cleaned:
                continue

            if normalized in seen:
                continue

            seen.add(normalized)
            result.append(cleaned)

        return result


content_brief_service = ContentBriefService()
