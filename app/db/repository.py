from uuid import UUID

from sqlalchemy import (
    desc,
    func,
    select,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from app.db.models import (
    ArticleRecord,
    ArticleVersionRecord,
    ContentBriefRecord,
    ContentProject,
    DocumentChunkRecord,
    DocumentImageRecord,
    GeneratedFileRecord,
    ImageBatch,
    KeywordStrategyRecord,
    ResearchRun,
    SEOMetadataRecord,
    UploadedDocument,
    UploadedImageRecord,
)
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


class ContentRepository:
    async def list_projects(
        self,
        session: AsyncSession,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[
        list[ContentProject],
        int,
    ]:
        count_result = await session.execute(
            select(
                func.count(
                    ContentProject.id
                )
            )
        )

        total = int(
            count_result.scalar_one()
        )

        result = await session.execute(
            select(
                ContentProject
            )
            .order_by(
                desc(
                    ContentProject.created_at
                )
            )
            .limit(limit)
            .offset(offset)
        )

        projects = list(
            result.scalars().all()
        )

        return projects, total

    async def get_project(
        self,
        session: AsyncSession,
        project_id: UUID,
    ) -> ContentProject | None:
        result = await session.execute(
            select(
                ContentProject
            ).where(
                ContentProject.id
                == project_id
            )
        )

        return result.scalar_one_or_none()

    async def create_project(
        self,
        session: AsyncSession,
        request: ContentGenerateRequest,
    ) -> ContentProject:
        project = ContentProject(
            topic=request.topic,
            country_code=request.country_code,
            language=request.language,
            article_type=request.article_type,
            tone=request.tone,
            content_goal=request.content_goal,
            status="generating",
            current_stage="research",
            request_payload=(
                request.model_dump(
                    mode="json"
                )
            ),
        )

        session.add(project)
        await session.commit()
        await session.refresh(project)
        return project

    async def update_project_stage(
        self,
        session: AsyncSession,
        project_id: UUID,
        stage: str,
    ) -> None:
        project = await session.get(
            ContentProject,
            project_id,
        )

        if project is None:
            raise ValueError(
                "Content project not found."
            )

        project.current_stage = stage
        project.status = "generating"

        await session.commit()

    async def mark_project_completed(
        self,
        session: AsyncSession,
        project_id: UUID,
    ) -> None:
        project = await session.get(
            ContentProject,
            project_id,
        )

        if project is None:
            return

        project.status = "completed"
        project.current_stage = "completed"
        project.error_stage = None
        project.error_message = None

        await session.commit()

    async def mark_project_failed(
        self,
        session: AsyncSession,
        project_id: UUID,
        stage: str,
        message: str,
    ) -> None:
        project = await session.get(
            ContentProject,
            project_id,
        )

        if project is None:
            return

        project.status = "failed"
        project.current_stage = stage
        project.error_stage = stage
        project.error_message = message

        await session.commit()

    async def save_research(
        self,
        session: AsyncSession,
        project_id: UUID,
        research: ResearchResult,
    ) -> ResearchRun:
        version = await self._next_version(
            session=session,
            model=ResearchRun,
            project_id=project_id,
        )

        record = ResearchRun(
            project_id=project_id,
            version=version,
            source_count=len(
                research.sources
            ),
            payload=research.model_dump(
                mode="json"
            ),
        )

        session.add(record)
        await session.commit()
        await session.refresh(record)
        return record

    async def save_keywords(
        self,
        session: AsyncSession,
        project_id: UUID,
        keywords: KeywordResult,
    ) -> KeywordStrategyRecord:
        version = await self._next_version(
            session=session,
            model=KeywordStrategyRecord,
            project_id=project_id,
        )

        record = KeywordStrategyRecord(
            project_id=project_id,
            version=version,
            primary_keyword=(
                keywords
                .primary_keyword
                .keyword
            ),
            search_intent=(
                keywords
                .search_intent
                .primary_intent
            ),
            payload=keywords.model_dump(
                mode="json"
            ),
        )

        session.add(record)
        await session.commit()
        await session.refresh(record)
        return record

    async def save_content_brief(
        self,
        session: AsyncSession,
        project_id: UUID,
        brief: ContentBriefResult,
    ) -> ContentBriefRecord:
        version = await self._next_version(
            session=session,
            model=ContentBriefRecord,
            project_id=project_id,
        )

        record = ContentBriefRecord(
            project_id=project_id,
            version=version,
            recommended_title=(
                brief.recommended_title
            ),
            target_word_count=(
                brief.target_word_count
            ),
            payload=brief.model_dump(
                mode="json"
            ),
        )

        session.add(record)
        await session.commit()
        await session.refresh(record)
        return record

    async def save_article(
        self,
        session: AsyncSession,
        project_id: UUID,
        article: ArticleResult,
    ) -> tuple[
        ArticleRecord,
        ArticleVersionRecord,
    ]:
        result = await session.execute(
            select(
                ArticleRecord
            ).where(
                ArticleRecord.project_id
                == project_id
            )
        )

        article_record = (
            result.scalar_one_or_none()
        )

        if article_record is None:
            article_record = ArticleRecord(
                project_id=project_id,
                title=article.title,
                current_version_number=0,
            )

            session.add(
                article_record
            )

            await session.flush()

        next_version = (
            article_record
            .current_version_number
            + 1
        )

        version_record = (
            ArticleVersionRecord(
                article_id=(
                    article_record.id
                ),
                version_number=(
                    next_version
                ),
                word_count=(
                    article.total_word_count
                ),
                article_markdown=(
                    article.article_markdown
                ),
                payload=article.model_dump(
                    mode="json"
                ),
            )
        )

        session.add(
            version_record
        )

        article_record.title = (
            article.title
        )
        article_record.current_version_number = (
            next_version
        )

        await session.commit()
        await session.refresh(
            article_record
        )
        await session.refresh(
            version_record
        )

        return (
            article_record,
            version_record,
        )

    async def save_seo(
        self,
        session: AsyncSession,
        project_id: UUID,
        article_version_id: UUID,
        seo: SEOResult,
    ) -> SEOMetadataRecord:
        version = await self._next_version(
            session=session,
            model=SEOMetadataRecord,
            project_id=project_id,
        )

        record = SEOMetadataRecord(
            project_id=project_id,
            article_version_id=(
                article_version_id
            ),
            version=version,
            slug=seo.slug,
            canonical_url=(
                seo.canonical_url
            ),
            readiness_score=(
                seo.readiness_score
            ),
            payload=seo.model_dump(
                mode="json"
            ),
        )

        session.add(record)
        await session.commit()
        await session.refresh(record)
        return record

    async def save_generated_html(
        self,
        session: AsyncSession,
        project_id: UUID,
        article_version_id: UUID,
        seo_metadata_id: UUID,
        html: HTMLRenderResult,
    ) -> GeneratedFileRecord:
        record = GeneratedFileRecord(
            project_id=project_id,
            article_version_id=(
                article_version_id
            ),
            seo_metadata_id=(
                seo_metadata_id
            ),
            file_type="html",
            filename=html.filename,
            relative_path=(
                html.relative_path
            ),
            full_html=html.full_html,
            article_html=(
                html.article_html
            ),
        )

        session.add(record)
        await session.commit()
        await session.refresh(record)
        return record

    async def _latest_project_record(
        self,
        session: AsyncSession,
        model,
        project_id: UUID,
    ):
        result = await session.execute(
            select(
                model
            )
            .where(
                model.project_id
                == project_id
            )
            .order_by(
                desc(
                    model.version
                )
            )
            .limit(1)
        )

        return result.scalar_one_or_none()

    async def get_latest_research(
        self,
        session: AsyncSession,
        project_id: UUID,
    ) -> ResearchRun | None:
        return await self._latest_project_record(
            session=session,
            model=ResearchRun,
            project_id=project_id,
        )

    async def get_latest_keywords(
        self,
        session: AsyncSession,
        project_id: UUID,
    ) -> KeywordStrategyRecord | None:
        return await self._latest_project_record(
            session=session,
            model=KeywordStrategyRecord,
            project_id=project_id,
        )

    async def get_latest_content_brief(
        self,
        session: AsyncSession,
        project_id: UUID,
    ) -> ContentBriefRecord | None:
        return await self._latest_project_record(
            session=session,
            model=ContentBriefRecord,
            project_id=project_id,
        )

    async def get_latest_seo(
        self,
        session: AsyncSession,
        project_id: UUID,
    ) -> SEOMetadataRecord | None:
        return await self._latest_project_record(
            session=session,
            model=SEOMetadataRecord,
            project_id=project_id,
        )

    async def get_article_by_project(
        self,
        session: AsyncSession,
        project_id: UUID,
    ) -> ArticleRecord | None:
        result = await session.execute(
            select(
                ArticleRecord
            )
            .where(
                ArticleRecord.project_id
                == project_id
            )
        )

        return result.scalar_one_or_none()

    async def get_current_article_version(
        self,
        session: AsyncSession,
        article: ArticleRecord,
    ) -> ArticleVersionRecord | None:
        result = await session.execute(
            select(
                ArticleVersionRecord
            )
            .where(
                ArticleVersionRecord.article_id
                == article.id
            )
            .where(
                ArticleVersionRecord.version_number
                == article.current_version_number
            )
        )

        return result.scalar_one_or_none()

    async def list_article_versions(
        self,
        session: AsyncSession,
        article_id: UUID,
    ) -> list[ArticleVersionRecord]:
        result = await session.execute(
            select(
                ArticleVersionRecord
            )
            .where(
                ArticleVersionRecord.article_id
                == article_id
            )
            .order_by(
                desc(
                    ArticleVersionRecord
                    .version_number
                )
            )
        )

        return list(
            result.scalars().all()
        )

    async def get_article_version(
        self,
        session: AsyncSession,
        article_id: UUID,
        version_number: int,
    ) -> ArticleVersionRecord | None:
        result = await session.execute(
            select(
                ArticleVersionRecord
            )
            .where(
                ArticleVersionRecord.article_id
                == article_id
            )
            .where(
                ArticleVersionRecord.version_number
                == version_number
            )
        )

        return result.scalar_one_or_none()

    async def get_usage_summary(
        self,
        session: AsyncSession,
    ) -> dict:
        counts_result = await session.execute(
            select(
                func.count(
                    ContentProject.id
                ),
                func.count(
                    ContentProject.id
                ).filter(
                    ContentProject.status
                    == "completed"
                ),
                func.count(
                    ContentProject.id
                ).filter(
                    ContentProject.status
                    == "failed"
                ),
            )
        )

        (
            total_projects,
            completed_projects,
            failed_projects,
        ) = counts_result.one()

        words_result = await session.execute(
            select(
                func.coalesce(
                    func.sum(
                        ArticleVersionRecord.word_count
                    ),
                    0,
                )
            )
            .select_from(ContentProject)
            .join(
                ArticleRecord,
                ArticleRecord.project_id
                == ContentProject.id,
            )
            .join(
                ArticleVersionRecord,
                (
                    ArticleVersionRecord.article_id
                    == ArticleRecord.id
                )
                & (
                    ArticleVersionRecord
                    .version_number
                    == ArticleRecord
                    .current_version_number
                ),
            )
        )

        total_words_written = (
            words_result.scalar_one()
        )

        return {
            "total_projects": total_projects,
            "completed_projects": (
                completed_projects
            ),
            "failed_projects": failed_projects,
            "total_words_written": (
                total_words_written
            ),
        }

    async def list_sitemap_entries(
        self,
        session: AsyncSession,
    ) -> list[tuple[str, object]]:
        # DISTINCT ON + ORDER BY version DESC gets the latest SEO
        # record per project in one query.
        result = await session.execute(
            select(
                SEOMetadataRecord.canonical_url,
                SEOMetadataRecord.updated_at,
            )
            .distinct(
                SEOMetadataRecord.project_id
            )
            .join(
                ContentProject,
                ContentProject.id
                == SEOMetadataRecord.project_id,
            )
            .where(
                ContentProject.status
                == "completed"
            )
            .order_by(
                SEOMetadataRecord.project_id,
                desc(SEOMetadataRecord.version),
            )
        )

        return list(result.all())

    async def get_latest_generated_file(
        self,
        session: AsyncSession,
        project_id: UUID,
    ) -> GeneratedFileRecord | None:
        result = await session.execute(
            select(
                GeneratedFileRecord
            )
            .where(
                GeneratedFileRecord.project_id
                == project_id
            )
            .order_by(
                desc(
                    GeneratedFileRecord.created_at
                )
            )
            .limit(1)
        )

        return result.scalar_one_or_none()

    async def save_document_with_chunks(
        self,
        session: AsyncSession,
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
    ) -> UploadedDocument:
        document = UploadedDocument(
            id=document_id,
            filename=filename,
            file_type=file_type,
            storage_bucket=storage_bucket,
            storage_path=storage_path,
            file_size_bytes=file_size_bytes,
            char_count=char_count,
            page_count=page_count,
            chunk_count=len(chunks),
            status="ready",
        )

        session.add(document)
        await session.flush()

        for index, (
            content,
            page_number,
            embedding,
        ) in enumerate(chunks):
            session.add(
                DocumentChunkRecord(
                    document_id=document.id,
                    chunk_index=index,
                    page_number=page_number,
                    content=content,
                    token_count=len(
                        content.split()
                    ),
                    embedding=embedding,
                )
            )

        await session.commit()
        await session.refresh(document)
        return document

    async def get_document(
        self,
        session: AsyncSession,
        document_id: UUID,
    ) -> UploadedDocument | None:
        result = await session.execute(
            select(
                UploadedDocument
            ).where(
                UploadedDocument.id
                == document_id
            )
        )

        return result.scalar_one_or_none()

    async def get_document_by_project(
        self,
        session: AsyncSession,
        project_id: UUID,
    ) -> UploadedDocument | None:
        result = await session.execute(
            select(
                UploadedDocument
            )
            .where(
                UploadedDocument.project_id
                == project_id
            )
            .order_by(
                desc(
                    UploadedDocument.created_at
                )
            )
            .limit(1)
        )

        return result.scalar_one_or_none()

    async def save_document_images(
        self,
        session: AsyncSession,
        document_id: UUID,
        storage_bucket: str,
        images: list[
            tuple[
                str,
                str,
                str,
                int,
                int,
                int,
                int | None,
            ]
        ],
    ) -> list[DocumentImageRecord]:
        records = []

        for index, (
            storage_path,
            public_url,
            content_type,
            width,
            height,
            file_size_bytes,
            page_number,
        ) in enumerate(images):
            record = DocumentImageRecord(
                document_id=document_id,
                order_index=index,
                page_number=page_number,
                storage_bucket=storage_bucket,
                storage_path=storage_path,
                public_url=public_url,
                content_type=content_type,
                width=width,
                height=height,
                file_size_bytes=file_size_bytes,
            )
            session.add(record)
            records.append(record)

        await session.commit()

        for record in records:
            await session.refresh(record)

        return records

    async def list_document_images(
        self,
        session: AsyncSession,
        document_id: UUID,
    ) -> list[DocumentImageRecord]:
        result = await session.execute(
            select(
                DocumentImageRecord
            )
            .where(
                DocumentImageRecord.document_id
                == document_id
            )
            .order_by(
                DocumentImageRecord.order_index
            )
        )

        return list(
            result.scalars().all()
        )

    async def save_image_batch(
        self,
        session: AsyncSession,
        batch_id: UUID,
        storage_bucket: str,
        images: list[
            tuple[
                str,
                str,
                str,
                str,
                int,
                int,
                int,
            ]
        ],
    ) -> ImageBatch:
        batch = ImageBatch(
            id=batch_id,
            image_count=len(images),
            status="ready",
        )

        session.add(batch)
        await session.flush()

        for index, (
            filename,
            storage_path,
            public_url,
            content_type,
            width,
            height,
            file_size_bytes,
        ) in enumerate(images):
            session.add(
                UploadedImageRecord(
                    batch_id=batch.id,
                    order_index=index,
                    filename=filename,
                    storage_bucket=storage_bucket,
                    storage_path=storage_path,
                    public_url=public_url,
                    content_type=content_type,
                    width=width,
                    height=height,
                    file_size_bytes=file_size_bytes,
                )
            )

        await session.commit()
        await session.refresh(batch)
        return batch

    async def get_image_batch(
        self,
        session: AsyncSession,
        batch_id: UUID,
    ) -> ImageBatch | None:
        result = await session.execute(
            select(
                ImageBatch
            ).where(
                ImageBatch.id == batch_id
            )
        )

        return result.scalar_one_or_none()

    async def get_image_batch_by_project(
        self,
        session: AsyncSession,
        project_id: UUID,
    ) -> ImageBatch | None:
        result = await session.execute(
            select(
                ImageBatch
            )
            .where(
                ImageBatch.project_id == project_id
            )
            .order_by(
                desc(ImageBatch.created_at)
            )
            .limit(1)
        )

        return result.scalar_one_or_none()

    async def list_batch_images(
        self,
        session: AsyncSession,
        batch_id: UUID,
    ) -> list[UploadedImageRecord]:
        result = await session.execute(
            select(
                UploadedImageRecord
            )
            .where(
                UploadedImageRecord.batch_id
                == batch_id
            )
            .order_by(
                UploadedImageRecord.order_index
            )
        )

        return list(
            result.scalars().all()
        )

    async def link_image_batch_to_project(
        self,
        session: AsyncSession,
        batch_id: UUID,
        project_id: UUID,
    ) -> None:
        batch = await session.get(
            ImageBatch,
            batch_id,
        )

        if batch is None:
            return

        batch.project_id = project_id
        await session.commit()

    async def get_uploaded_image(
        self,
        session: AsyncSession,
        image_id: UUID,
    ) -> UploadedImageRecord | None:
        result = await session.execute(
            select(
                UploadedImageRecord
            ).where(
                UploadedImageRecord.id == image_id
            )
        )

        return result.scalar_one_or_none()

    async def update_uploaded_image(
        self,
        session: AsyncSession,
        image_id: UUID,
        storage_path: str,
        public_url: str,
        content_type: str,
        width: int,
        height: int,
        file_size_bytes: int,
    ) -> UploadedImageRecord:
        image = await session.get(
            UploadedImageRecord,
            image_id,
        )

        if image is None:
            raise ValueError(
                "Uploaded image not found."
            )

        image.storage_path = storage_path
        image.public_url = public_url
        image.content_type = content_type
        image.width = width
        image.height = height
        image.file_size_bytes = file_size_bytes

        await session.commit()
        await session.refresh(image)
        return image

    async def list_documents(
        self,
        session: AsyncSession,
    ) -> list[UploadedDocument]:
        result = await session.execute(
            select(
                UploadedDocument
            )
            .order_by(
                desc(
                    UploadedDocument.created_at
                )
            )
        )

        return list(
            result.scalars().all()
        )

    async def link_document_to_project(
        self,
        session: AsyncSession,
        document_id: UUID,
        project_id: UUID,
    ) -> None:
        document = await session.get(
            UploadedDocument,
            document_id,
        )

        if document is None:
            return

        document.project_id = project_id
        await session.commit()

    async def search_document_chunks(
        self,
        session: AsyncSession,
        document_id: UUID,
        query_embedding: list[float],
        top_k: int = 6,
    ) -> list[DocumentChunkRecord]:
        result = await session.execute(
            select(
                DocumentChunkRecord
            )
            .where(
                DocumentChunkRecord.document_id
                == document_id
            )
            .order_by(
                DocumentChunkRecord
                .embedding
                .cosine_distance(
                    query_embedding
                )
            )
            .limit(top_k)
        )

        return list(
            result.scalars().all()
        )

    async def _next_version(
        self,
        session: AsyncSession,
        model,
        project_id: UUID,
    ) -> int:
        result = await session.execute(
            select(
                func.coalesce(
                    func.max(
                        model.version
                    ),
                    0,
                )
                + 1
            ).where(
                model.project_id
                == project_id
            )
        )

        return int(
            result.scalar_one()
        )


content_repository = ContentRepository()
