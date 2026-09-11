import json

from app.prompts.keywords import (
    KEYWORD_STRATEGY_PROMPT,
)
from app.schemas.keywords import (
    KeywordItem,
    KeywordRequest,
    KeywordResult,
    KeywordStrategyAI,
)
from app.services.openai_service import (
    openai_service,
)


class KeywordService:
    def __init__(self) -> None:
        self.client = openai_service.client
        self.model = openai_service.model

    async def build_strategy(
        self,
        request: KeywordRequest,
    ) -> KeywordResult:
        payload = self._build_payload(request)

        response = await self.client.responses.parse(
            model=self.model,
            instructions=KEYWORD_STRATEGY_PROMPT,
            input=json.dumps(
                payload,
                ensure_ascii=False,
            ),
            text_format=KeywordStrategyAI,
            store=False,
        )

        strategy = response.output_parsed

        if strategy is None:
            raise ValueError(
                "OpenAI did not return a valid "
                "keyword strategy."
            )

        strategy = self._normalize_strategy(
            strategy
        )

        return KeywordResult(
            topic=request.research.topic,
            search_intent=strategy.search_intent,
            primary_keyword=(
                strategy.primary_keyword
            ),
            secondary_keywords=(
                strategy.secondary_keywords
            ),
            semantic_terms=(
                strategy.semantic_terms
            ),
            long_tail_keywords=(
                strategy.long_tail_keywords
            ),
            question_keywords=(
                strategy.question_keywords
            ),
            must_cover_topics=(
                strategy.must_cover_topics
            ),
            title_directions=(
                strategy.title_directions
            ),
            heading_terms=(
                strategy.heading_terms
            ),
            internal_link_topics=(
                strategy.internal_link_topics
            ),
            differentiation_opportunities=(
                strategy.differentiation_opportunities
            ),
            metrics_status="not_connected",
        )

    def _build_payload(
        self,
        request: KeywordRequest,
    ) -> dict:
        research = request.research

        return {
            "topic": research.topic,
            "language": request.language,
            "country_code": (
                request.country_code
            ),
            "target_audience": (
                request.target_audience
            ),
            "content_goal": (
                request.content_goal
            ),
            "research_search_intent": (
                research.search_intent
            ),
            "research_summary": (
                research.summary
            ),
            "questions_to_answer": (
                research.questions_to_answer
            ),
            "key_facts": [
                {
                    "claim": fact.claim,
                    "source_urls": (
                        fact.source_urls
                    ),
                }
                for fact in research.key_facts
            ],
            "statistics": [
                {
                    "claim": fact.claim,
                    "source_urls": (
                        fact.source_urls
                    ),
                }
                for fact in research.statistics
            ],
            "recent_developments": [
                {
                    "claim": fact.claim,
                    "source_urls": (
                        fact.source_urls
                    ),
                }
                for fact in (
                    research.recent_developments
                )
            ],
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
            "article_angles": (
                research.article_angles
            ),
        }

    def _normalize_strategy(
        self,
        strategy: KeywordStrategyAI,
    ) -> KeywordStrategyAI:
        primary = (
            strategy
            .primary_keyword
            .keyword
            .strip()
            .casefold()
        )

        strategy.secondary_keywords = (
            self._dedupe_keyword_items(
                strategy.secondary_keywords,
                excluded={primary},
            )
        )

        strategy.long_tail_keywords = (
            self._dedupe_keyword_items(
                strategy.long_tail_keywords,
                excluded={primary},
            )
        )

        strategy.question_keywords = (
            self._dedupe_keyword_items(
                strategy.question_keywords,
                excluded={primary},
            )
        )

        strategy.semantic_terms = (
            self._dedupe_strings(
                strategy.semantic_terms
            )
        )

        strategy.must_cover_topics = (
            self._dedupe_strings(
                strategy.must_cover_topics
            )
        )

        strategy.title_directions = (
            self._dedupe_strings(
                strategy.title_directions
            )
        )

        strategy.heading_terms = (
            self._dedupe_strings(
                strategy.heading_terms
            )
        )

        strategy.internal_link_topics = (
            self._dedupe_strings(
                strategy.internal_link_topics
            )
        )

        strategy.differentiation_opportunities = (
            self._dedupe_strings(
                strategy
                .differentiation_opportunities
            )
        )

        return strategy

    def _dedupe_keyword_items(
        self,
        items: list[KeywordItem],
        excluded: set[str] | None = None,
    ) -> list[KeywordItem]:
        excluded = excluded or set()
        seen: set[str] = set()
        result: list[KeywordItem] = []

        for item in items:
            keyword = item.keyword.strip()
            normalized = keyword.casefold()

            if not keyword:
                continue

            if normalized in excluded:
                continue

            if normalized in seen:
                continue

            seen.add(normalized)

            result.append(
                item.model_copy(
                    update={
                        "keyword": keyword
                    }
                )
            )

        return result

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


keyword_service = KeywordService()
