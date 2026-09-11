from uuid import UUID

from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from app.core.exceptions import (
    ContentPipelineError,
)
from app.core.monitoring import (
    capture_exception,
)
from app.db.repository import (
    content_repository,
)
from app.schemas.article import (
    ArticleRequest,
)
from app.schemas.content import (
    ContentGenerateRequest,
    ContentGenerateResult,
)
from app.schemas.content_brief import (
    ContentBriefRequest,
)
from app.schemas.html import (
    HTMLRenderRequest,
)
from app.schemas.keywords import (
    KeywordRequest,
)
from app.schemas.document import (
    DocumentResearchRequest,
)
from app.schemas.image_upload import (
    ImageResearchRequest,
)
from app.schemas.research import (
    ResearchRequest,
    ResearchResult,
)
from app.schemas.seo import (
    SEORequest,
)
from app.services.article_service import (
    article_service,
)
from app.services.content_brief_service import (
    content_brief_service,
)
from app.services.document_research_service import (
    document_research_service,
)
from app.services.html_service import (
    html_service,
)
from app.services.image_placement import (
    assign_images_from_citations,
    distribute_images_across_sections,
)
from app.services.image_research_service import (
    image_research_service,
)
from app.services.keyword_service import (
    keyword_service,
)
from app.services.research_merge import (
    merge_research_results,
)
from app.services.research_service import (
    research_service,
)
from app.services.seo_service import (
    seo_service,
)


class ContentPipelineService:
    async def generate(
        self,
        request: ContentGenerateRequest,
        session: AsyncSession,
    ) -> ContentGenerateResult:
        project = (
            await content_repository.create_project(
                session=session,
                request=request,
            )
        )

        stage = "research"

        try:
            await content_repository.update_project_stage(
                session=session,
                project_id=project.id,
                stage="research",
            )

            (
                research,
                grounding_image_urls,
            ) = await self._run_research(
                session=session,
                project_id=project.id,
                request=request,
            )

            await content_repository.save_research(
                session=session,
                project_id=project.id,
                research=research,
            )

            stage = "keyword_strategy"

            await content_repository.update_project_stage(
                session=session,
                project_id=project.id,
                stage=stage,
            )

            keywords = (
                await keyword_service.build_strategy(
                    KeywordRequest(
                        research=research,
                        language=(
                            request.language
                        ),
                        country_code=(
                            request.country_code
                        ),
                        target_audience=(
                            request.target_audience
                        ),
                        content_goal=(
                            request.content_goal
                        ),
                    )
                )
            )

            await content_repository.save_keywords(
                session=session,
                project_id=project.id,
                keywords=keywords,
            )

            stage = "content_brief"

            await content_repository.update_project_stage(
                session=session,
                project_id=project.id,
                stage=stage,
            )

            content_brief = (
                await content_brief_service.create_brief(
                    ContentBriefRequest(
                        research=research,
                        keywords=keywords,
                        article_type=(
                            request.article_type
                        ),
                        tone=request.tone,
                        target_audience=(
                            request.target_audience
                        ),
                        target_word_count=(
                            request.target_word_count
                        ),
                        brand_name=(
                            request.brand_name
                            or request.site_name
                        ),
                        call_to_action=(
                            request.call_to_action
                        ),
                    )
                )
            )

            await content_repository.save_content_brief(
                session=session,
                project_id=project.id,
                brief=content_brief,
            )

            stage = "article_generation"

            await content_repository.update_project_stage(
                session=session,
                project_id=project.id,
                stage=stage,
            )

            article = (
                await article_service.generate_article(
                    ArticleRequest(
                        research=research,
                        brief=content_brief,
                        language=(
                            request.language
                        ),
                        additional_instructions=(
                            request
                            .additional_instructions
                        ),
                    )
                )
            )

            # The first featured image is used as the header/OG
            # image (see html_service.py) — any additional ones
            # the user selected get spaced through the body instead
            # of sitting unused, so more than one image is actually
            # visible in the rendered post.
            featured_image_urls = [
                str(url)
                for url in request.featured_image_urls
            ]

            if grounding_image_urls and featured_image_urls:
                # Image-batch mode: only ever show images the user
                # explicitly checked as featured — every uploaded
                # image informs the writing (vision analysis), but
                # an image the model happened to cite that the user
                # never selected should not appear in the output.
                allowed_image_urls = set(
                    featured_image_urls
                )

                article = assign_images_from_citations(
                    article,
                    allowed_urls=allowed_image_urls,
                )

                used_urls = {
                    url
                    for section in article.sections
                    for url in section.image_urls
                }
                leftover_urls = [
                    url
                    for url in featured_image_urls[1:]
                    if url not in used_urls
                ]

                if leftover_urls:
                    article = (
                        distribute_images_across_sections(
                            article, leftover_urls
                        )
                    )
            elif len(featured_image_urls) > 1:
                article = (
                    distribute_images_across_sections(
                        article,
                        featured_image_urls[1:],
                    )
                )

            (
                article_record,
                article_version_record,
            ) = await content_repository.save_article(
                session=session,
                project_id=project.id,
                article=article,
            )

            stage = "seo"

            await content_repository.update_project_stage(
                session=session,
                project_id=project.id,
                stage=stage,
            )

            seo = await seo_service.generate_seo(
                SEORequest(
                    article=article,
                    brief=content_brief,
                    site_name=(
                        request.effective_site_name
                    ),
                    site_url=(
                        request.effective_site_url
                    ),
                    article_path_prefix=(
                        request
                        .article_path_prefix
                    ),
                    authors=(
                        request.authors
                    ),
                    publisher_name=(
                        request.publisher_name
                    ),
                    publisher_url=(
                        request.publisher_url
                    ),
                    publisher_logo_url=(
                        request
                        .publisher_logo_url
                    ),
                    featured_image_urls=(
                        request
                        .featured_image_urls
                    ),
                    thumbnail_image_url=(
                        request
                        .thumbnail_image_url
                    ),
                    slug_override=(
                        request.slug_override
                    ),
                    date_published=(
                        request.date_published
                    ),
                    date_modified=(
                        request.date_modified
                    ),
                    indexable=(
                        request.indexable
                    ),
                    schema_type_override=(
                        request
                        .schema_type_override
                    ),
                )
            )

            seo_record = (
                await content_repository.save_seo(
                    session=session,
                    project_id=project.id,
                    article_version_id=(
                        article_version_record.id
                    ),
                    seo=seo,
                )
            )

            stage = "html_rendering"

            await content_repository.update_project_stage(
                session=session,
                project_id=project.id,
                stage=stage,
            )

            html = html_service.render(
                HTMLRenderRequest(
                    article=article,
                    seo=seo,
                    language_code=(
                        request.language_code
                    ),
                    text_direction=(
                        request.text_direction
                    ),
                    featured_image_alt=(
                        request.featured_image_alt
                    ),
                    include_sources=(
                        request.include_sources
                    ),
                    save_file=(
                        request.save_html_file
                    ),
                )
            )

            await content_repository.save_generated_html(
                session=session,
                project_id=project.id,
                article_version_id=(
                    article_version_record.id
                ),
                seo_metadata_id=(
                    seo_record.id
                ),
                html=html,
            )

            await content_repository.mark_project_completed(
                session=session,
                project_id=project.id,
            )

            return ContentGenerateResult(
                project_id=project.id,
                article_id=article_record.id,
                article_version=(
                    article_version_record
                    .version_number
                ),
                research=research,
                keywords=keywords,
                content_brief=content_brief,
                article=article,
                seo=seo,
                html=html,
            )
        except Exception as exc:
            await content_repository.mark_project_failed(
                session=session,
                project_id=project.id,
                stage=stage,
                message=str(exc),
            )

            capture_exception(
                exc,
                project_id=str(project.id),
                stage=stage,
            )

            raise ContentPipelineError(
                stage=stage,
                message=str(exc),
            ) from exc

    async def _run_research(
        self,
        session: AsyncSession,
        project_id: UUID,
        request: ContentGenerateRequest,
    ) -> tuple[ResearchResult, list[str]]:
        if request.image_batch_id:
            return await self._run_image_research(
                session=session,
                project_id=project_id,
                request=request,
            )

        if request.document_id:
            research = await self._run_document_research(
                session=session,
                project_id=project_id,
                request=request,
            )
            return research, []

        research = await research_service.research(
            ResearchRequest(
                topic=request.topic,
                country_code=request.country_code,
                language=request.language,
                freshness=request.freshness,
                max_queries=(
                    request.max_research_queries
                ),
            )
        )
        return research, []

    async def _run_document_research(
        self,
        session: AsyncSession,
        project_id: UUID,
        request: ContentGenerateRequest,
    ) -> ResearchResult:
        document = await content_repository.get_document(
            session=session,
            document_id=request.document_id,
        )

        if document is None:
            raise ValueError(
                "Uploaded document not found."
            )

        if document.status != "ready":
            raise ValueError(
                "Uploaded document is not ready yet "
                f"(status: {document.status})."
            )

        await content_repository.link_document_to_project(
            session=session,
            document_id=document.id,
            project_id=project_id,
        )

        document_research = (
            await document_research_service.research(
                session=session,
                document=document,
                request=DocumentResearchRequest(
                    document_id=document.id,
                    topic=request.topic,
                    language=request.language,
                    max_queries=(
                        request.max_research_queries
                    ),
                ),
            )
        )

        if not request.use_web_research:
            return document_research

        web_research = await research_service.research(
            ResearchRequest(
                topic=request.topic,
                country_code=request.country_code,
                language=request.language,
                freshness=request.freshness,
                max_queries=(
                    request.max_research_queries
                ),
            )
        )

        return merge_research_results(
            document_research,
            web_research,
        )

    async def _run_image_research(
        self,
        session: AsyncSession,
        project_id: UUID,
        request: ContentGenerateRequest,
    ) -> tuple[ResearchResult, list[str]]:
        batch = await content_repository.get_image_batch(
            session=session,
            batch_id=request.image_batch_id,
        )

        if batch is None:
            raise ValueError(
                "Uploaded image batch not found."
            )

        images = await content_repository.list_batch_images(
            session=session,
            batch_id=batch.id,
        )

        if not images:
            raise ValueError(
                "Uploaded image batch has no images."
            )

        await content_repository.link_image_batch_to_project(
            session=session,
            batch_id=batch.id,
            project_id=project_id,
        )

        image_research = (
            await image_research_service.research(
                batch=batch,
                images=images,
                request=ImageResearchRequest(
                    batch_id=batch.id,
                    topic=request.topic,
                    language=request.language,
                ),
            )
        )

        image_urls = [
            image.public_url for image in images
        ]

        if not request.use_web_research:
            return image_research, image_urls

        web_research = await research_service.research(
            ResearchRequest(
                topic=request.topic,
                country_code=request.country_code,
                language=request.language,
                freshness=request.freshness,
                max_queries=(
                    request.max_research_queries
                ),
            )
        )

        return (
            merge_research_results(
                image_research, web_research
            ),
            image_urls,
        )


content_pipeline_service = (
    ContentPipelineService()
)
