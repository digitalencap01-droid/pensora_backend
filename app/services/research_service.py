import asyncio
import json
from datetime import date
from urllib.parse import urlparse

from app.prompts.research import (
    QUERY_PLANNER_PROMPT,
    SYNTHESIS_PROMPT,
    WEB_RESEARCH_PROMPT,
)
from app.schemas.research import (
    ResearchQueryPlan,
    ResearchRequest,
    ResearchResult,
    ResearchSource,
    ResearchSynthesis,
)
from app.services.openai_service import openai_service


class ResearchService:
    def __init__(self) -> None:
        self.client = openai_service.client
        self.model = openai_service.model
        self.search_semaphore = asyncio.Semaphore(3)

    async def research(
        self,
        request: ResearchRequest,
    ) -> ResearchResult:
        query_plan = await self._create_query_plan(request)
        queries = query_plan.queries[: request.max_queries]

        search_results = await asyncio.gather(
            *[
                self._search_web(
                    query=query,
                    request=request,
                )
                for query in queries
            ]
        )

        sources = self._merge_sources(search_results)

        synthesis = await self._synthesize_research(
            request=request,
            query_plan=query_plan,
            search_results=search_results,
            sources=sources,
        )

        return ResearchResult(
            topic=request.topic,
            search_intent=synthesis.search_intent,
            summary=synthesis.summary,
            queries_used=queries,
            questions_to_answer=synthesis.questions_to_answer,
            key_facts=synthesis.key_facts,
            statistics=synthesis.statistics,
            recent_developments=synthesis.recent_developments,
            important_entities=synthesis.important_entities,
            controversies_or_uncertainties=(
                synthesis.controversies_or_uncertainties
            ),
            content_gaps=synthesis.content_gaps,
            article_angles=synthesis.article_angles,
            sources=sources,
        )

    async def _create_query_plan(
        self,
        request: ResearchRequest,
    ) -> ResearchQueryPlan:
        current_date = date.today().isoformat()

        response = await self.client.responses.parse(
            model=self.model,
            instructions=QUERY_PLANNER_PROMPT,
            input=f"""
Topic:
{request.topic}

Target country:
{request.country_code}

Language:
{request.language}

Preferred freshness:
{request.freshness}

Current date:
{current_date}

Generate {request.max_queries} distinct research queries.
""",
            text_format=ResearchQueryPlan,
            store=False,
        )

        if response.output_parsed is None:
            raise ValueError(
                "OpenAI did not return a valid research query plan."
            )

        return response.output_parsed

    async def _search_web(
        self,
        query: str,
        request: ResearchRequest,
    ) -> dict:
        async with self.search_semaphore:
            current_date = date.today().isoformat()

            web_search_tool = {
                "type": "web_search",
                "search_context_size": "medium",
                "external_web_access": True,
                "user_location": {
                    "type": "approximate",
                    "country": request.country_code,
                },
            }

            response = await self.client.responses.create(
                model=self.model,
                instructions=WEB_RESEARCH_PROMPT,
                tools=[web_search_tool],
                tool_choice="required",
                include=[
                    "web_search_call.action.sources",
                ],
                input=f"""
Research query:

{query}

Current date:
{current_date}

Preferred freshness:
{request.freshness}

Target country:
{request.country_code}

Output language:
{request.language}

When freshness is relevant, prioritize information within the requested
freshness period. Older authoritative sources may still be used for
background information.
""",
                store=False,
            )

            return {
                "query": query,
                "research_text": response.output_text,
                "sources": self._extract_sources(response),
            }

    def _extract_sources(
        self,
        response: object,
    ) -> list[ResearchSource]:
        response_data = response.model_dump()

        discovered_sources: dict[str, ResearchSource] = {}

        for item in response_data.get("output", []):
            if item.get("type") == "web_search_call":
                action = item.get("action") or {}

                for source in action.get("sources") or []:
                    url = source.get("url")
                    if not url:
                        continue

                    self._add_source(
                        discovered_sources,
                        url=url,
                        title=source.get("title"),
                    )

            if item.get("type") == "message":
                for content in item.get("content") or []:
                    for annotation in content.get("annotations") or []:
                        if annotation.get("type") != "url_citation":
                            continue

                        url = annotation.get("url")
                        if not url:
                            continue

                        self._add_source(
                            discovered_sources,
                            url=url,
                            title=annotation.get("title"),
                        )

        return list(discovered_sources.values())

    def _add_source(
        self,
        sources: dict[str, ResearchSource],
        url: str,
        title: str | None,
    ) -> None:
        if not url.startswith(("http://", "https://")):
            return

        normalized_url = url.strip()
        if normalized_url in sources:
            return

        domain = (
            urlparse(normalized_url)
            .netloc
            .lower()
            .removeprefix("www.")
        )

        sources[normalized_url] = ResearchSource(
            title=title,
            url=normalized_url,
            domain=domain,
        )

    def _merge_sources(
        self,
        search_results: list[dict],
    ) -> list[ResearchSource]:
        merged: dict[str, ResearchSource] = {}

        for result in search_results:
            for source in result["sources"]:
                if source.url not in merged:
                    merged[source.url] = source

        return list(merged.values())

    async def _synthesize_research(
        self,
        request: ResearchRequest,
        query_plan: ResearchQueryPlan,
        search_results: list[dict],
        sources: list[ResearchSource],
    ) -> ResearchSynthesis:
        source_urls = [
            source.url
            for source in sources
        ]

        research_payload = {
            "topic": request.topic,
            "search_intent": query_plan.search_intent,
            "questions_to_answer": query_plan.questions_to_answer,
            "research": [
                {
                    "query": result["query"],
                    "research_text": result["research_text"],
                    "source_urls": [
                        source.url
                        for source in result["sources"]
                    ],
                }
                for result in search_results
            ],
            "allowed_source_urls": source_urls,
        }

        response = await self.client.responses.parse(
            model=self.model,
            instructions=SYNTHESIS_PROMPT,
            input=json.dumps(
                research_payload,
                ensure_ascii=False,
            ),
            text_format=ResearchSynthesis,
            store=False,
        )

        if response.output_parsed is None:
            raise ValueError(
                "OpenAI did not return valid research synthesis."
            )

        return response.output_parsed


research_service = ResearchService()
