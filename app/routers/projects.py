from uuid import UUID
from xml.sax.saxutils import escape

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Response,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from app.db.database import (
    get_db_session,
)
from app.db.repository import (
    content_repository,
)
from app.schemas.document import (
    DocumentImageListResult,
)
from app.schemas.project_management import (
    ArticleMutationResult,
    ArticleUpdateRequest,
    ArticleVersionDetail,
    ArticleVersionListResult,
    ProjectArtifactsResult,
    ProjectDetail,
    ProjectListResult,
    RebuildOutputResult,
    RegenerateSectionRequest,
    UsageSummary,
)
from app.services.project_management_service import (
    project_management_service,
)


router = APIRouter(
    prefix="/api/v1/projects",
    tags=["Projects"],
)


@router.get(
    "",
    response_model=ProjectListResult,
)
async def list_projects(
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    session: AsyncSession = Depends(
        get_db_session
    ),
) -> ProjectListResult:
    return (
        await project_management_service
        .list_projects(
            session=session,
            limit=limit,
            offset=offset,
        )
    )


@router.get(
    "/usage-summary",
    response_model=UsageSummary,
)
async def get_usage_summary(
    session: AsyncSession = Depends(
        get_db_session
    ),
) -> UsageSummary:
    return (
        await project_management_service
        .get_usage_summary(
            session=session,
        )
    )


@router.get(
    "/sitemap.xml"
)
async def get_sitemap(
    session: AsyncSession = Depends(
        get_db_session
    ),
) -> Response:
    # Registered before /{project_id} so "sitemap.xml" isn't matched
    # as a project id.
    entries = (
        await content_repository
        .list_sitemap_entries(
            session=session,
        )
    )

    urls = "".join(
        f"<url><loc>{escape(canonical_url)}</loc>"
        f"<lastmod>{updated_at.date().isoformat()}</lastmod>"
        "</url>"
        for canonical_url, updated_at in entries
    )

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns='
        '"http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"{urls}"
        "</urlset>"
    )

    return Response(
        content=xml,
        media_type="application/xml",
    )


@router.get(
    "/robots.txt"
)
async def get_robots(
    site_url: str | None = Query(
        default=None,
        description=(
            "The domain this robots.txt will be "
            "hosted on, used to point at the "
            "matching sitemap."
        ),
    ),
) -> Response:
    lines = [
        "User-agent: *",
        "Allow: /",
    ]

    if site_url:
        lines += [
            "",
            "Sitemap: "
            f"{site_url.rstrip('/')}/sitemap.xml",
        ]

    return Response(
        content="\n".join(lines) + "\n",
        media_type="text/plain",
    )


@router.get(
    "/{project_id}",
    response_model=ProjectDetail,
)
async def get_project(
    project_id: UUID,
    session: AsyncSession = Depends(
        get_db_session
    ),
) -> ProjectDetail:
    try:
        return (
            await project_management_service
            .get_project(
                session=session,
                project_id=project_id,
            )
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


@router.get(
    "/{project_id}/artifacts",
    response_model=ProjectArtifactsResult,
)
async def get_project_artifacts(
    project_id: UUID,
    session: AsyncSession = Depends(
        get_db_session
    ),
) -> ProjectArtifactsResult:
    try:
        return (
            await project_management_service
            .get_artifacts(
                session=session,
                project_id=project_id,
            )
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


@router.get(
    "/{project_id}/document-images",
    response_model=DocumentImageListResult,
)
async def get_project_document_images(
    project_id: UUID,
    session: AsyncSession = Depends(
        get_db_session
    ),
) -> DocumentImageListResult:
    try:
        return (
            await project_management_service
            .get_document_images(
                session=session,
                project_id=project_id,
            )
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


@router.get(
    "/{project_id}/article/versions",
    response_model=(
        ArticleVersionListResult
    ),
)
async def list_article_versions(
    project_id: UUID,
    session: AsyncSession = Depends(
        get_db_session
    ),
) -> ArticleVersionListResult:
    try:
        return (
            await project_management_service
            .list_versions(
                session=session,
                project_id=project_id,
            )
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


@router.get(
    "/{project_id}/article/versions/{version_number}",
    response_model=ArticleVersionDetail,
)
async def get_article_version(
    project_id: UUID,
    version_number: int,
    session: AsyncSession = Depends(
        get_db_session
    ),
) -> ArticleVersionDetail:
    try:
        return (
            await project_management_service
            .get_version(
                session=session,
                project_id=project_id,
                version_number=(
                    version_number
                ),
            )
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


@router.put(
    "/{project_id}/article",
    response_model=ArticleMutationResult,
)
async def update_article(
    project_id: UUID,
    request: ArticleUpdateRequest,
    session: AsyncSession = Depends(
        get_db_session
    ),
) -> ArticleMutationResult:
    try:
        return (
            await project_management_service
            .update_article(
                session=session,
                project_id=project_id,
                updated_article=(
                    request.article
                ),
            )
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@router.post(
    "/{project_id}/article/versions/{version_number}/restore",
    response_model=ArticleMutationResult,
)
async def restore_article_version(
    project_id: UUID,
    version_number: int,
    session: AsyncSession = Depends(
        get_db_session
    ),
) -> ArticleMutationResult:
    try:
        return (
            await project_management_service
            .restore_version(
                session=session,
                project_id=project_id,
                version_number=(
                    version_number
                ),
            )
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@router.post(
    "/{project_id}/article/regenerate-section",
    response_model=ArticleMutationResult,
)
async def regenerate_article_section(
    project_id: UUID,
    request: RegenerateSectionRequest,
    session: AsyncSession = Depends(
        get_db_session
    ),
) -> ArticleMutationResult:
    try:
        return (
            await project_management_service
            .regenerate_section(
                session=session,
                project_id=project_id,
                section_id=(
                    request.section_id
                ),
                instructions=(
                    request.instructions
                ),
            )
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@router.post(
    "/{project_id}/rebuild-output",
    response_model=RebuildOutputResult,
)
async def rebuild_output(
    project_id: UUID,
    session: AsyncSession = Depends(
        get_db_session
    ),
) -> RebuildOutputResult:
    try:
        return (
            await project_management_service
            .rebuild_outputs(
                session=session,
                project_id=project_id,
            )
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
