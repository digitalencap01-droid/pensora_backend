from __future__ import annotations

import math
from types import SimpleNamespace
from uuid import UUID

from app.db.supabase_rest import row, supabase_rest
from app.schemas.article import (
    ArticleResult,
)
from app.schemas.content import (
    ContentGenerateRequest,
)
from app.schemas.content_brief import (
    ContentBriefResult,
)
from app.schemas.html import (
    HTMLRenderResult,
)
from app.schemas.keywords import (
    KeywordResult,
)
from app.schemas.research import (
    ResearchResult,
)
from app.schemas.seo import (
    SEOResult,
)


def _vector_literal(embedding: list[float]) -> str:
    # pgvector's text input format — sent as a plain string, Postgres
    # casts it to `vector` on the way in.
    return "[" + ",".join(repr(float(x)) for x in embedding) + "]"


def _parse_vector(value) -> list[float]:
    if isinstance(value, list):
        return [float(x) for x in value]
    text = str(value).strip().strip("[]")
    if not text:
        return []
    return [float(x) for x in text.split(",")]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class ContentRepository:
    async def list_projects(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[SimpleNamespace], int]:
        total = await supabase_rest.count("content_projects")

        rows = await supabase_rest.select(
            "content_projects",
            params={
                "select": "*",
                "order": "created_at.desc",
                "limit": str(limit),
                "offset": str(offset),
            },
        )

        return [row(r) for r in rows], total

    async def get_project(
        self,
        project_id: UUID,
    ) -> SimpleNamespace | None:
        data = await supabase_rest.select_one(
            "content_projects",
            params={"id": f"eq.{project_id}"},
        )
        return row(data) if data else None

    async def create_project(
        self,
        request: ContentGenerateRequest,
    ) -> SimpleNamespace:
        data = {
            "topic": request.topic,
            "country_code": request.country_code,
            "language": request.language,
            "article_type": request.article_type,
            "tone": request.tone,
            "content_goal": request.content_goal,
            "status": "generating",
            "current_stage": "research",
            "request_payload": request.model_dump(
                mode="json"
            ),
        }

        result = await supabase_rest.insert_one(
            "content_projects", data
        )
        return row(result)

    async def update_project_stage(
        self,
        project_id: UUID,
        stage: str,
    ) -> None:
        result = await supabase_rest.update(
            "content_projects",
            {"current_stage": stage, "status": "generating"},
            params={"id": f"eq.{project_id}"},
        )

        if not result:
            raise ValueError(
                "Content project not found."
            )

    async def mark_project_completed(
        self,
        project_id: UUID,
    ) -> None:
        await supabase_rest.update(
            "content_projects",
            {
                "status": "completed",
                "current_stage": "completed",
                "error_stage": None,
                "error_message": None,
            },
            params={"id": f"eq.{project_id}"},
        )

    async def mark_project_failed(
        self,
        project_id: UUID,
        stage: str,
        message: str,
    ) -> None:
        await supabase_rest.update(
            "content_projects",
            {
                "status": "failed",
                "current_stage": stage,
                "error_stage": stage,
                "error_message": message,
            },
            params={"id": f"eq.{project_id}"},
        )

    async def save_research(
        self,
        project_id: UUID,
        research: ResearchResult,
    ) -> SimpleNamespace:
        version = await self._next_version(
            "research_runs", project_id
        )

        data = {
            "project_id": project_id,
            "version": version,
            "source_count": len(research.sources),
            "payload": research.model_dump(mode="json"),
        }

        result = await supabase_rest.insert_one(
            "research_runs", data
        )
        return row(result)

    async def save_keywords(
        self,
        project_id: UUID,
        keywords: KeywordResult,
    ) -> SimpleNamespace:
        version = await self._next_version(
            "keyword_strategies", project_id
        )

        data = {
            "project_id": project_id,
            "version": version,
            "primary_keyword": (
                keywords.primary_keyword.keyword
            ),
            "search_intent": (
                keywords.search_intent.primary_intent
            ),
            "payload": keywords.model_dump(mode="json"),
        }

        result = await supabase_rest.insert_one(
            "keyword_strategies", data
        )
        return row(result)

    async def save_content_brief(
        self,
        project_id: UUID,
        brief: ContentBriefResult,
    ) -> SimpleNamespace:
        version = await self._next_version(
            "content_briefs", project_id
        )

        data = {
            "project_id": project_id,
            "version": version,
            "recommended_title": brief.recommended_title,
            "target_word_count": brief.target_word_count,
            "payload": brief.model_dump(mode="json"),
        }

        result = await supabase_rest.insert_one(
            "content_briefs", data
        )
        return row(result)

    async def save_article(
        self,
        project_id: UUID,
        article: ArticleResult,
    ) -> tuple[SimpleNamespace, SimpleNamespace]:
        existing = await supabase_rest.select_one(
            "articles",
            params={"project_id": f"eq.{project_id}"},
        )

        if existing is None:
            existing = await supabase_rest.insert_one(
                "articles",
                {
                    "project_id": project_id,
                    "title": article.title,
                    "current_version_number": 0,
                },
            )

        next_version = (
            existing["current_version_number"] + 1
        )

        version_result = await supabase_rest.insert_one(
            "article_versions",
            {
                "article_id": existing["id"],
                "version_number": next_version,
                "word_count": article.total_word_count,
                "article_markdown": (
                    article.article_markdown
                ),
                "payload": article.model_dump(mode="json"),
            },
        )

        updated = await supabase_rest.update(
            "articles",
            {
                "title": article.title,
                "current_version_number": next_version,
            },
            params={"id": f"eq.{existing['id']}"},
        )

        return row(updated[0]), row(version_result)

    async def save_seo(
        self,
        project_id: UUID,
        article_version_id: UUID,
        seo: SEOResult,
    ) -> SimpleNamespace:
        version = await self._next_version(
            "seo_metadata", project_id
        )

        data = {
            "project_id": project_id,
            "article_version_id": article_version_id,
            "version": version,
            "slug": seo.slug,
            "canonical_url": seo.canonical_url,
            "readiness_score": seo.readiness_score,
            "payload": seo.model_dump(mode="json"),
        }

        result = await supabase_rest.insert_one(
            "seo_metadata", data
        )
        return row(result)

    async def save_generated_html(
        self,
        project_id: UUID,
        article_version_id: UUID,
        seo_metadata_id: UUID,
        html: HTMLRenderResult,
    ) -> SimpleNamespace:
        data = {
            "project_id": project_id,
            "article_version_id": article_version_id,
            "seo_metadata_id": seo_metadata_id,
            "file_type": "html",
            "filename": html.filename,
            "relative_path": html.relative_path,
            "full_html": html.full_html,
            "article_html": html.article_html,
        }

        result = await supabase_rest.insert_one(
            "generated_files", data
        )
        return row(result)

    async def _latest_project_record(
        self,
        table: str,
        project_id: UUID,
    ) -> SimpleNamespace | None:
        data = await supabase_rest.select_one(
            table,
            params={
                "project_id": f"eq.{project_id}",
                "order": "version.desc",
            },
        )
        return row(data) if data else None

    async def get_latest_research(
        self, project_id: UUID
    ) -> SimpleNamespace | None:
        return await self._latest_project_record(
            "research_runs", project_id
        )

    async def get_latest_keywords(
        self, project_id: UUID
    ) -> SimpleNamespace | None:
        return await self._latest_project_record(
            "keyword_strategies", project_id
        )

    async def get_latest_content_brief(
        self, project_id: UUID
    ) -> SimpleNamespace | None:
        return await self._latest_project_record(
            "content_briefs", project_id
        )

    async def get_latest_seo(
        self, project_id: UUID
    ) -> SimpleNamespace | None:
        return await self._latest_project_record(
            "seo_metadata", project_id
        )

    async def get_article_by_project(
        self, project_id: UUID
    ) -> SimpleNamespace | None:
        data = await supabase_rest.select_one(
            "articles",
            params={"project_id": f"eq.{project_id}"},
        )
        return row(data) if data else None

    async def get_current_article_version(
        self, article: SimpleNamespace
    ) -> SimpleNamespace | None:
        data = await supabase_rest.select_one(
            "article_versions",
            params={
                "article_id": f"eq.{article.id}",
                "version_number": (
                    f"eq.{article.current_version_number}"
                ),
            },
        )
        return row(data) if data else None

    async def list_article_versions(
        self, article_id: UUID
    ) -> list[SimpleNamespace]:
        rows = await supabase_rest.select(
            "article_versions",
            params={
                "article_id": f"eq.{article_id}",
                "order": "version_number.desc",
            },
        )
        return [row(r) for r in rows]

    async def get_article_version(
        self,
        article_id: UUID,
        version_number: int,
    ) -> SimpleNamespace | None:
        data = await supabase_rest.select_one(
            "article_versions",
            params={
                "article_id": f"eq.{article_id}",
                "version_number": f"eq.{version_number}",
            },
        )
        return row(data) if data else None

    async def get_usage_summary(self) -> dict:
        projects = await supabase_rest.select(
            "content_projects",
            params={"select": "id,status"},
        )

        total_projects = len(projects)
        completed_projects = sum(
            1
            for p in projects
            if p["status"] == "completed"
        )
        failed_projects = sum(
            1 for p in projects if p["status"] == "failed"
        )

        articles = await supabase_rest.select(
            "articles",
            params={
                "select": "id,current_version_number"
            },
        )

        total_words_written = 0

        if articles:
            ids = ",".join(
                str(a["id"]) for a in articles
            )
            versions = await supabase_rest.select(
                "article_versions",
                params={
                    "article_id": f"in.({ids})",
                    "select": (
                        "article_id,version_number,"
                        "word_count"
                    ),
                },
            )
            current_by_article = {
                a["id"]: a["current_version_number"]
                for a in articles
            }
            total_words_written = sum(
                v["word_count"]
                for v in versions
                if v["version_number"]
                == current_by_article.get(
                    v["article_id"]
                )
            )

        return {
            "total_projects": total_projects,
            "completed_projects": completed_projects,
            "failed_projects": failed_projects,
            "total_words_written": total_words_written,
        }

    async def list_sitemap_entries(
        self,
    ) -> list[tuple[str, object]]:
        completed = await supabase_rest.select(
            "content_projects",
            params={
                "select": "id",
                "status": "eq.completed",
            },
        )

        if not completed:
            return []

        ids = ",".join(str(p["id"]) for p in completed)

        seo_rows = await supabase_rest.select(
            "seo_metadata",
            params={
                "project_id": f"in.({ids})",
                "select": (
                    "project_id,canonical_url,"
                    "version,updated_at"
                ),
                "order": "project_id.asc,version.desc",
            },
        )

        seen: set = set()
        entries: list[tuple[str, object]] = []

        for entry in seo_rows:
            project_id = entry["project_id"]
            if project_id in seen:
                continue
            seen.add(project_id)
            entries.append(
                (
                    entry["canonical_url"],
                    entry["updated_at"],
                )
            )

        return entries

    async def get_latest_generated_file(
        self, project_id: UUID
    ) -> SimpleNamespace | None:
        data = await supabase_rest.select_one(
            "generated_files",
            params={
                "project_id": f"eq.{project_id}",
                "order": "created_at.desc",
            },
        )
        return row(data) if data else None

    async def save_document_with_chunks(
        self,
        document_id: UUID,
        filename: str,
        file_type: str,
        storage_bucket: str,
        storage_path: str,
        file_size_bytes: int,
        char_count: int,
        page_count: int | None,
        chunks: list[
            tuple[str, int | None, list[float]]
        ],
    ) -> SimpleNamespace:
        document = await supabase_rest.insert_one(
            "uploaded_documents",
            {
                "id": document_id,
                "filename": filename,
                "file_type": file_type,
                "storage_bucket": storage_bucket,
                "storage_path": storage_path,
                "file_size_bytes": file_size_bytes,
                "char_count": char_count,
                "page_count": page_count,
                "chunk_count": len(chunks),
                "status": "ready",
            },
        )

        if chunks:
            chunk_rows = [
                {
                    "document_id": document["id"],
                    "chunk_index": index,
                    "page_number": page_number,
                    "content": content,
                    "token_count": len(content.split()),
                    "embedding": _vector_literal(
                        embedding
                    ),
                }
                for index, (
                    content,
                    page_number,
                    embedding,
                ) in enumerate(chunks)
            ]
            await supabase_rest.insert(
                "document_chunks", chunk_rows
            )

        return row(document)

    async def get_document(
        self, document_id: UUID
    ) -> SimpleNamespace | None:
        data = await supabase_rest.select_one(
            "uploaded_documents",
            params={"id": f"eq.{document_id}"},
        )
        return row(data) if data else None

    async def get_document_by_project(
        self, project_id: UUID
    ) -> SimpleNamespace | None:
        data = await supabase_rest.select_one(
            "uploaded_documents",
            params={
                "project_id": f"eq.{project_id}",
                "order": "created_at.desc",
            },
        )
        return row(data) if data else None

    async def save_document_images(
        self,
        document_id: UUID,
        storage_bucket: str,
        images: list[
            tuple[
                str, str, str, int, int, int, int | None
            ]
        ],
    ) -> list[SimpleNamespace]:
        if not images:
            return []

        image_rows = [
            {
                "document_id": document_id,
                "order_index": index,
                "page_number": page_number,
                "storage_bucket": storage_bucket,
                "storage_path": storage_path,
                "public_url": public_url,
                "content_type": content_type,
                "width": width,
                "height": height,
                "file_size_bytes": file_size_bytes,
            }
            for index, (
                storage_path,
                public_url,
                content_type,
                width,
                height,
                file_size_bytes,
                page_number,
            ) in enumerate(images)
        ]

        result = await supabase_rest.insert(
            "document_images", image_rows
        )
        return [row(r) for r in result]

    async def list_document_images(
        self, document_id: UUID
    ) -> list[SimpleNamespace]:
        rows = await supabase_rest.select(
            "document_images",
            params={
                "document_id": f"eq.{document_id}",
                "order": "order_index.asc",
            },
        )
        return [row(r) for r in rows]

    async def save_image_batch(
        self,
        batch_id: UUID,
        storage_bucket: str,
        images: list[
            tuple[str, str, str, str, int, int, int]
        ],
    ) -> SimpleNamespace:
        batch = await supabase_rest.insert_one(
            "image_batches",
            {
                "id": batch_id,
                "image_count": len(images),
                "status": "ready",
            },
        )

        if images:
            image_rows = [
                {
                    "batch_id": batch["id"],
                    "order_index": index,
                    "filename": filename,
                    "storage_bucket": storage_bucket,
                    "storage_path": storage_path,
                    "public_url": public_url,
                    "content_type": content_type,
                    "width": width,
                    "height": height,
                    "file_size_bytes": file_size_bytes,
                }
                for index, (
                    filename,
                    storage_path,
                    public_url,
                    content_type,
                    width,
                    height,
                    file_size_bytes,
                ) in enumerate(images)
            ]
            await supabase_rest.insert(
                "uploaded_images", image_rows
            )

        return row(batch)

    async def get_image_batch(
        self, batch_id: UUID
    ) -> SimpleNamespace | None:
        data = await supabase_rest.select_one(
            "image_batches",
            params={"id": f"eq.{batch_id}"},
        )
        return row(data) if data else None

    async def get_image_batch_by_project(
        self, project_id: UUID
    ) -> SimpleNamespace | None:
        data = await supabase_rest.select_one(
            "image_batches",
            params={
                "project_id": f"eq.{project_id}",
                "order": "created_at.desc",
            },
        )
        return row(data) if data else None

    async def list_batch_images(
        self, batch_id: UUID
    ) -> list[SimpleNamespace]:
        rows = await supabase_rest.select(
            "uploaded_images",
            params={
                "batch_id": f"eq.{batch_id}",
                "order": "order_index.asc",
            },
        )
        return [row(r) for r in rows]

    async def link_image_batch_to_project(
        self,
        batch_id: UUID,
        project_id: UUID,
    ) -> None:
        await supabase_rest.update(
            "image_batches",
            {"project_id": project_id},
            params={"id": f"eq.{batch_id}"},
        )

    async def get_uploaded_image(
        self, image_id: UUID
    ) -> SimpleNamespace | None:
        data = await supabase_rest.select_one(
            "uploaded_images",
            params={"id": f"eq.{image_id}"},
        )
        return row(data) if data else None

    async def update_uploaded_image(
        self,
        image_id: UUID,
        storage_path: str,
        public_url: str,
        content_type: str,
        width: int,
        height: int,
        file_size_bytes: int,
    ) -> SimpleNamespace:
        result = await supabase_rest.update(
            "uploaded_images",
            {
                "storage_path": storage_path,
                "public_url": public_url,
                "content_type": content_type,
                "width": width,
                "height": height,
                "file_size_bytes": file_size_bytes,
            },
            params={"id": f"eq.{image_id}"},
        )

        if not result:
            raise ValueError(
                "Uploaded image not found."
            )

        return row(result[0])

    async def list_documents(
        self,
    ) -> list[SimpleNamespace]:
        rows = await supabase_rest.select(
            "uploaded_documents",
            params={"order": "created_at.desc"},
        )
        return [row(r) for r in rows]

    async def link_document_to_project(
        self,
        document_id: UUID,
        project_id: UUID,
    ) -> None:
        await supabase_rest.update(
            "uploaded_documents",
            {"project_id": project_id},
            params={"id": f"eq.{document_id}"},
        )

    async def search_document_chunks(
        self,
        document_id: UUID,
        query_embedding: list[float],
        top_k: int = 6,
    ) -> list[SimpleNamespace]:
        rows = await supabase_rest.select(
            "document_chunks",
            params={"document_id": f"eq.{document_id}"},
        )

        scored = [
            (
                _cosine_similarity(
                    query_embedding,
                    _parse_vector(r["embedding"]),
                ),
                r,
            )
            for r in rows
        ]
        scored.sort(key=lambda pair: pair[0], reverse=True)

        return [row(r) for _, r in scored[:top_k]]

    async def _next_version(
        self,
        table: str,
        project_id: UUID,
    ) -> int:
        data = await supabase_rest.select_one(
            table,
            params={
                "project_id": f"eq.{project_id}",
                "select": "version",
                "order": "version.desc",
            },
        )
        return (data["version"] + 1) if data else 1


content_repository = ContentRepository()
