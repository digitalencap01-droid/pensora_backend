from uuid import UUID

from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from app.db.repository import (
    content_repository,
)
from app.schemas.article import (
    ArticleRequest,
    ArticleResult,
)
from app.schemas.content import (
    ContentGenerateRequest,
)
from app.schemas.content_brief import (
    ContentBriefResult,
)
from app.schemas.document import (
    DocumentImageListResult,
    DocumentImageSummary,
)
from app.schemas.html import (
    HTMLRenderRequest,
    HTMLRenderResult,
)
from app.schemas.keywords import (
    KeywordResult,
)
from app.schemas.project_management import (
    ArticleMutationResult,
    ArticleVersionDetail,
    ArticleVersionListResult,
    ArticleVersionSummary,
    ProjectArtifactsResult,
    ProjectDetail,
    ProjectListResult,
    ProjectSummary,
    RebuildOutputResult,
    UsageSummary,
)
from app.schemas.research import (
    ResearchResult,
)
from app.schemas.seo import (
    SEORequest,
    SEOResult,
)
from app.services.article_service import (
    article_service,
)
from app.services.html_service import (
    html_service,
)
from app.services.seo_service import (
    seo_service,
)


class ProjectManagementService:
    async def list_projects(
        self,
        session: AsyncSession,
        limit: int,
        offset: int,
    ) -> ProjectListResult:
        projects, total = (
            await content_repository.list_projects(
                session=session,
                limit=limit,
                offset=offset,
            )
        )

        return ProjectListResult(
            items=[
                self._project_summary(
                    project
                )
                for project in projects
            ],
            total=total,
            limit=limit,
            offset=offset,
        )

    async def get_usage_summary(
        self,
        session: AsyncSession,
    ) -> UsageSummary:
        summary = (
            await content_repository
            .get_usage_summary(
                session=session,
            )
        )

        return UsageSummary(**summary)

    async def get_project(
        self,
        session: AsyncSession,
        project_id: UUID,
    ) -> ProjectDetail:
        project = (
            await self._require_project(
                session,
                project_id,
            )
        )

        return ProjectDetail(
            **self._project_summary(
                project
            ).model_dump(),
            content_goal=(
                project.content_goal
            ),
            request_payload=(
                project.request_payload
            ),
            error_message=(
                project.error_message
            ),
        )

    async def get_artifacts(
        self,
        session: AsyncSession,
        project_id: UUID,
    ) -> ProjectArtifactsResult:
        await self._require_project(
            session,
            project_id,
        )

        research_record = (
            await content_repository
            .get_latest_research(
                session,
                project_id,
            )
        )
        keyword_record = (
            await content_repository
            .get_latest_keywords(
                session,
                project_id,
            )
        )
        brief_record = (
            await content_repository
            .get_latest_content_brief(
                session,
                project_id,
            )
        )
        seo_record = (
            await content_repository
            .get_latest_seo(
                session,
                project_id,
            )
        )
        file_record = (
            await content_repository
            .get_latest_generated_file(
                session,
                project_id,
            )
        )
        article_record = (
            await content_repository
            .get_article_by_project(
                session,
                project_id,
            )
        )

        article = None

        if article_record:
            version_record = (
                await content_repository
                .get_current_article_version(
                    session,
                    article_record,
                )
            )

            if version_record:
                article = (
                    ArticleResult.model_validate(
                        version_record.payload
                    )
                )

        return ProjectArtifactsResult(
            project_id=project_id,
            research=(
                ResearchResult.model_validate(
                    research_record.payload
                )
                if research_record
                else None
            ),
            keywords=(
                KeywordResult.model_validate(
                    keyword_record.payload
                )
                if keyword_record
                else None
            ),
            content_brief=(
                ContentBriefResult.model_validate(
                    brief_record.payload
                )
                if brief_record
                else None
            ),
            article=article,
            seo=(
                SEOResult.model_validate(
                    seo_record.payload
                )
                if seo_record
                else None
            ),
            html=(
                HTMLRenderResult(
                    filename=(
                        file_record.filename
                    ),
                    full_html=(
                        file_record.full_html
                    ),
                    article_html=(
                        file_record.article_html
                    ),
                    saved=bool(
                        file_record.relative_path
                    ),
                    relative_path=(
                        file_record.relative_path
                    ),
                )
                if file_record
                else None
            ),
        )

    async def get_document_images(
        self,
        session: AsyncSession,
        project_id: UUID,
    ) -> DocumentImageListResult:
        # Despite the name (kept for API stability), this surfaces
        # every image available for this project's editor gallery —
        # from an uploaded document's extracted figures, or from a
        # directly uploaded image batch, whichever grounded it.
        await self._require_project(
            session,
            project_id,
        )

        summaries: list[DocumentImageSummary] = []

        document = (
            await content_repository
            .get_document_by_project(
                session=session,
                project_id=project_id,
            )
        )

        if document is not None:
            document_images = (
                await content_repository
                .list_document_images(
                    session=session,
                    document_id=document.id,
                )
            )
            summaries.extend(
                DocumentImageSummary(
                    id=image.id,
                    url=image.public_url,
                    page_number=image.page_number,
                    width=image.width,
                    height=image.height,
                )
                for image in document_images
            )

        image_batch = (
            await content_repository
            .get_image_batch_by_project(
                session=session,
                project_id=project_id,
            )
        )

        if image_batch is not None:
            batch_images = (
                await content_repository
                .list_batch_images(
                    session=session,
                    batch_id=image_batch.id,
                )
            )
            summaries.extend(
                DocumentImageSummary(
                    id=image.id,
                    url=image.public_url,
                    page_number=None,
                    width=image.width,
                    height=image.height,
                )
                for image in batch_images
            )

        return DocumentImageListResult(
            images=summaries
        )

    async def list_versions(
        self,
        session: AsyncSession,
        project_id: UUID,
    ) -> ArticleVersionListResult:
        article = await self._require_article(
            session,
            project_id,
        )

        versions = (
            await content_repository
            .list_article_versions(
                session,
                article.id,
            )
        )

        return ArticleVersionListResult(
            article_id=article.id,
            current_version_number=(
                article.current_version_number
            ),
            versions=[
                ArticleVersionSummary(
                    version_id=version.id,
                    version_number=(
                        version.version_number
                    ),
                    word_count=(
                        version.word_count
                    ),
                    created_at=(
                        version.created_at
                    ),
                )
                for version in versions
            ],
        )

    async def get_version(
        self,
        session: AsyncSession,
        project_id: UUID,
        version_number: int,
    ) -> ArticleVersionDetail:
        article = await self._require_article(
            session,
            project_id,
        )

        version = (
            await content_repository
            .get_article_version(
                session=session,
                article_id=article.id,
                version_number=version_number,
            )
        )

        if version is None:
            raise ValueError(
                "Article version not found."
            )

        return ArticleVersionDetail(
            article_id=article.id,
            version_id=version.id,
            version_number=(
                version.version_number
            ),
            article=(
                ArticleResult.model_validate(
                    version.payload
                )
            ),
        )

    async def update_article(
        self,
        session: AsyncSession,
        project_id: UUID,
        updated_article: ArticleResult,
    ) -> ArticleMutationResult:
        project = await self._require_project(
            session,
            project_id,
        )

        await self._require_article(
            session,
            project_id,
        )

        return await self._save_new_version_and_rebuild(
            session=session,
            project=project,
            article=updated_article,
        )

    async def restore_version(
        self,
        session: AsyncSession,
        project_id: UUID,
        version_number: int,
    ) -> ArticleMutationResult:
        old_version = await self.get_version(
            session=session,
            project_id=project_id,
            version_number=version_number,
        )

        project = await self._require_project(
            session,
            project_id,
        )

        return await self._save_new_version_and_rebuild(
            session=session,
            project=project,
            article=old_version.article,
        )

    async def regenerate_section(
        self,
        session: AsyncSession,
        project_id: UUID,
        section_id: str,
        instructions: str | None,
    ) -> ArticleMutationResult:
        project = await self._require_project(
            session,
            project_id,
        )

        artifacts = await self.get_artifacts(
            session,
            project_id,
        )

        if artifacts.research is None:
            raise ValueError(
                "Research data is missing."
            )

        if artifacts.content_brief is None:
            raise ValueError(
                "Content brief is missing."
            )

        if artifacts.article is None:
            raise ValueError(
                "Article is missing."
            )

        request_payload = (
            ContentGenerateRequest.model_validate(
                project.request_payload
            )
        )

        article_request = ArticleRequest(
            research=artifacts.research,
            brief=artifacts.content_brief,
            language=request_payload.language,
            additional_instructions=(
                request_payload
                .additional_instructions
            ),
        )

        regenerated_article = (
            await article_service
            .regenerate_section(
                request=article_request,
                current_article=(
                    artifacts.article
                ),
                section_id=section_id,
                instructions=instructions,
            )
        )

        return await self._save_new_version_and_rebuild(
            session=session,
            project=project,
            article=regenerated_article,
        )

    async def rebuild_outputs(
        self,
        session: AsyncSession,
        project_id: UUID,
    ) -> RebuildOutputResult:
        project = await self._require_project(
            session,
            project_id,
        )

        article_record = (
            await self._require_article(
                session,
                project_id,
            )
        )

        version_record = (
            await content_repository
            .get_current_article_version(
                session,
                article_record,
            )
        )

        if version_record is None:
            raise ValueError(
                "Current article version "
                "does not exist."
            )

        article = ArticleResult.model_validate(
            version_record.payload
        )

        seo, html = await self._rebuild_outputs_for_version(
            session=session,
            project=project,
            article=article,
            article_version_id=(
                version_record.id
            ),
        )

        return RebuildOutputResult(
            project_id=project.id,
            article_id=article_record.id,
            version_number=(
                version_record.version_number
            ),
            seo=seo,
            html=html,
        )

    async def _save_new_version_and_rebuild(
        self,
        session: AsyncSession,
        project,
        article: ArticleResult,
    ) -> ArticleMutationResult:
        (
            article_record,
            article_version,
        ) = await content_repository.save_article(
            session=session,
            project_id=project.id,
            article=article,
        )

        seo, html = await self._rebuild_outputs_for_version(
            session=session,
            project=project,
            article=article,
            article_version_id=(
                article_version.id
            ),
        )

        return ArticleMutationResult(
            project_id=project.id,
            article_id=article_record.id,
            article_version_id=(
                article_version.id
            ),
            version_number=(
                article_version.version_number
            ),
            article=article,
            seo=seo,
            html=html,
        )

    async def _rebuild_outputs_for_version(
        self,
        session: AsyncSession,
        project,
        article: ArticleResult,
        article_version_id: UUID,
    ) -> tuple[
        SEOResult,
        HTMLRenderResult,
    ]:
        brief_record = (
            await content_repository
            .get_latest_content_brief(
                session,
                project.id,
            )
        )

        if brief_record is None:
            raise ValueError(
                "Content brief is missing."
            )

        brief = ContentBriefResult.model_validate(
            brief_record.payload
        )

        original_request = (
            ContentGenerateRequest.model_validate(
                project.request_payload
            )
        )

        seo = await seo_service.generate_seo(
            SEORequest(
                article=article,
                brief=brief,
                site_name=(
                    original_request.effective_site_name
                ),
                site_url=(
                    original_request.effective_site_url
                ),
                article_path_prefix=(
                    original_request
                    .article_path_prefix
                ),
                authors=(
                    original_request.authors
                ),
                publisher_name=(
                    original_request.publisher_name
                ),
                publisher_url=(
                    original_request.publisher_url
                ),
                publisher_logo_url=(
                    original_request
                    .publisher_logo_url
                ),
                featured_image_urls=(
                    original_request
                    .featured_image_urls
                ),
                thumbnail_image_url=(
                    original_request
                    .thumbnail_image_url
                ),
                slug_override=(
                    original_request.slug_override
                ),
                date_published=(
                    original_request.date_published
                ),
                date_modified=(
                    original_request.date_modified
                ),
                indexable=(
                    original_request.indexable
                ),
                schema_type_override=(
                    original_request
                    .schema_type_override
                ),
            )
        )

        seo_record = (
            await content_repository.save_seo(
                session=session,
                project_id=project.id,
                article_version_id=(
                    article_version_id
                ),
                seo=seo,
            )
        )

        html = html_service.render(
            HTMLRenderRequest(
                article=article,
                seo=seo,
                language_code=(
                    original_request.language_code
                ),
                text_direction=(
                    original_request.text_direction
                ),
                featured_image_alt=(
                    original_request
                    .featured_image_alt
                ),
                include_sources=(
                    original_request
                    .include_sources
                ),
                save_file=(
                    original_request
                    .save_html_file
                ),
            )
        )

        await content_repository.save_generated_html(
            session=session,
            project_id=project.id,
            article_version_id=(
                article_version_id
            ),
            seo_metadata_id=(
                seo_record.id
            ),
            html=html,
        )

        return seo, html

    async def _require_project(
        self,
        session: AsyncSession,
        project_id: UUID,
    ):
        project = (
            await content_repository.get_project(
                session,
                project_id,
            )
        )

        if project is None:
            raise ValueError(
                "Content project not found."
            )

        return project

    async def _require_article(
        self,
        session: AsyncSession,
        project_id: UUID,
    ):
        await self._require_project(
            session,
            project_id,
        )

        article = (
            await content_repository
            .get_article_by_project(
                session,
                project_id,
            )
        )

        if article is None:
            raise ValueError(
                "Article not found."
            )

        return article

    def _project_summary(
        self,
        project,
    ) -> ProjectSummary:
        return ProjectSummary(
            id=project.id,
            topic=project.topic,
            status=project.status,
            current_stage=(
                project.current_stage
            ),
            article_type=(
                project.article_type
            ),
            tone=project.tone,
            language=project.language,
            country_code=(
                project.country_code
            ),
            error_stage=(
                project.error_stage
            ),
            webflow_item_id=(
                project.webflow_item_id
            ),
            webflow_publish_status=(
                project.webflow_publish_status
            ),
            created_at=(
                project.created_at
            ),
            updated_at=(
                project.updated_at
            ),
        )


project_management_service = (
    ProjectManagementService()
)
