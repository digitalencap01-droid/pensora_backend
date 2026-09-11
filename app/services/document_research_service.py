import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    DocumentChunkRecord,
    UploadedDocument,
)
from app.db.repository import content_repository
from app.prompts.document import (
    DOCUMENT_QUERY_PLANNER_PROMPT,
    DOCUMENT_SYNTHESIS_PROMPT,
)
from app.schemas.document import DocumentResearchRequest
from app.schemas.research import (
    ResearchQueryPlan,
    ResearchResult,
    ResearchSource,
    ResearchSynthesis,
)
from app.services.document_service import document_service
from app.services.openai_service import openai_service


class DocumentResearchService:
    def __init__(self) -> None:
        self.client = openai_service.client
        self.model = openai_service.model

    async def research(
        self,
        session: AsyncSession,
        document: UploadedDocument,
        request: DocumentResearchRequest,
    ) -> ResearchResult:
        query_plan = await self._create_query_plan(
            document=document,
            request=request,
        )
        queries = query_plan.queries[: request.max_queries]

        # The embedding calls are plain OpenAI requests and could run
        # concurrently, but a single AsyncSession can't have multiple
        # operations in flight against it at once — so the embeddings
        # are batched into one call, then each chunk lookup runs
        # sequentially against `session`.
        query_embeddings = await document_service.embed_texts(
            queries
        )

        retrieval_results: list[list[DocumentChunkRecord]] = []

        for query_embedding in query_embeddings:
            chunks = (
                await content_repository.search_document_chunks(
                    session=session,
                    document_id=document.id,
                    query_embedding=query_embedding,
                    top_k=request.chunks_per_query,
                )
            )
            retrieval_results.append(chunks)

        sources = self._build_sources(
            document=document,
            retrieval_results=retrieval_results,
        )

        synthesis = await self._synthesize(
            document=document,
            request=request,
            query_plan=query_plan,
            queries=queries,
            retrieval_results=retrieval_results,
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
        document: UploadedDocument,
        request: DocumentResearchRequest,
    ) -> ResearchQueryPlan:
        response = await self.client.responses.parse(
            model=self.model,
            instructions=DOCUMENT_QUERY_PLANNER_PROMPT,
            input=f"""
Topic:
{request.topic}

Uploaded document:
{document.filename}

Language:
{request.language}

Generate {request.max_queries} distinct lookup queries to search this
document for evidence relevant to the topic above.
""",
            text_format=ResearchQueryPlan,
            store=False,
        )

        if response.output_parsed is None:
            raise ValueError(
                "OpenAI did not return a valid document query plan."
            )

        return response.output_parsed

    def _chunk_url(
        self,
        document: UploadedDocument,
        chunk: DocumentChunkRecord,
    ) -> str:
        return f"doc://{document.id}/chunk/{chunk.chunk_index}"

    def _chunk_title(
        self,
        document: UploadedDocument,
        chunk: DocumentChunkRecord,
    ) -> str:
        if chunk.page_number:
            return f"{document.filename} — page {chunk.page_number}"

        return f"{document.filename} — part {chunk.chunk_index + 1}"

    def _build_sources(
        self,
        document: UploadedDocument,
        retrieval_results: list[list[DocumentChunkRecord]],
    ) -> list[ResearchSource]:
        sources: dict[str, ResearchSource] = {}

        for chunks in retrieval_results:
            for chunk in chunks:
                url = self._chunk_url(document, chunk)

                if url in sources:
                    continue

                sources[url] = ResearchSource(
                    title=self._chunk_title(document, chunk),
                    url=url,
                    domain=document.filename,
                )

        return list(sources.values())

    async def _synthesize(
        self,
        document: UploadedDocument,
        request: DocumentResearchRequest,
        query_plan: ResearchQueryPlan,
        queries: list[str],
        retrieval_results: list[list[DocumentChunkRecord]],
        sources: list[ResearchSource],
    ) -> ResearchSynthesis:
        payload = {
            "topic": request.topic,
            "document_filename": document.filename,
            "search_intent": query_plan.search_intent,
            "questions_to_answer": (
                query_plan.questions_to_answer
            ),
            "excerpts": [
                {
                    "query": query,
                    "chunks": [
                        {
                            "source_url": self._chunk_url(
                                document, chunk
                            ),
                            "content": chunk.content,
                        }
                        for chunk in chunks
                    ],
                }
                for query, chunks in zip(
                    queries, retrieval_results, strict=True
                )
            ],
            "allowed_source_urls": [
                source.url for source in sources
            ],
        }

        response = await self.client.responses.parse(
            model=self.model,
            instructions=DOCUMENT_SYNTHESIS_PROMPT,
            input=json.dumps(
                payload,
                ensure_ascii=False,
            ),
            text_format=ResearchSynthesis,
            store=False,
        )

        if response.output_parsed is None:
            raise ValueError(
                "OpenAI did not return a valid document synthesis."
            )

        return response.output_parsed


document_research_service = DocumentResearchService()
