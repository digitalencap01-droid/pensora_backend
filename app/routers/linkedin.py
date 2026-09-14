from fastapi import APIRouter, Query, Request
from app.schemas.linkedin import (
    LinkedInConnectResult,
    LinkedInGenerateRequest,
    LinkedInGenerateResult,
    LinkedInHashtagSuggestRequest,
    LinkedInHashtagSuggestResult,
    LinkedInPostPublishRequest,
    LinkedInPublishRequest,
    LinkedInPublishResult,
    LinkedInStatus,
)
from app.services.linkedin_service import linkedin_service


router = APIRouter(
    prefix="/api/v1/linkedin",
    tags=["LinkedIn"],
)


@router.get("/status", response_model=LinkedInStatus)
async def get_linkedin_status() -> LinkedInStatus:
    return await linkedin_service.get_status()


@router.get("/connect", response_model=LinkedInConnectResult)
async def connect_linkedin(
    request: Request,
    return_path: str = Query(default="/library"),
) -> LinkedInConnectResult:
    authorize_url = linkedin_service.build_authorization_url(
        return_path=return_path,
        request=request,
    )
    return LinkedInConnectResult(authorize_url=authorize_url)


@router.delete("/disconnect", status_code=204)
async def disconnect_linkedin() -> None:
    await linkedin_service.disconnect()


@router.post("/publish", response_model=LinkedInPublishResult)
async def publish_to_linkedin(
    request: LinkedInPublishRequest,
) -> LinkedInPublishResult:
    return await linkedin_service.publish_article(
        article_title=request.article_title,
        article_summary=request.article_summary,
        article_url=str(request.article_url),
        commentary=request.commentary,
    )


@router.post("/generate", response_model=LinkedInGenerateResult)
async def generate_linkedin_content(
    request: LinkedInGenerateRequest,
) -> LinkedInGenerateResult:
    text = await linkedin_service.generate_content(
        content_type=request.content_type,
        topic=request.topic,
        tone=request.tone,
        use_web_search=request.use_web_search,
        document_id=request.document_id,
        image_batch_id=request.image_batch_id,
    )
    hashtags = await linkedin_service.suggest_hashtags(
        topic=request.topic,
        content_type=request.content_type,
        draft_text=text,
    )
    return LinkedInGenerateResult(
        content_type=request.content_type,
        text=text,
        hashtags=hashtags,
    )


@router.post("/hashtags/suggest", response_model=LinkedInHashtagSuggestResult)
async def suggest_linkedin_hashtags(
    request: LinkedInHashtagSuggestRequest,
) -> LinkedInHashtagSuggestResult:
    hashtags = await linkedin_service.suggest_hashtags(
        topic=request.topic,
        content_type=request.content_type,
        draft_text=request.draft_text,
    )
    return LinkedInHashtagSuggestResult(hashtags=hashtags)


@router.post("/publish-post", response_model=LinkedInPublishResult)
async def publish_linkedin_post(
    request: LinkedInPostPublishRequest,
) -> LinkedInPublishResult:
    return await linkedin_service.publish_post(
        text=request.text,
    )
