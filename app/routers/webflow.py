from uuid import UUID

from fastapi import APIRouter, Query

from app.schemas.webflow import (
    WebflowCollectionsResult,
    WebflowConnectRequest,
    WebflowFieldsResult,
    WebflowPublishResult,
    WebflowSitesResult,
    WebflowStatus,
)
from app.services.webflow_service import webflow_service


router = APIRouter(
    prefix="/api/v1/webflow",
    tags=["Webflow"],
)


@router.get("/status", response_model=WebflowStatus)
async def get_webflow_status() -> WebflowStatus:
    return await webflow_service.get_status()


@router.get("/sites", response_model=WebflowSitesResult)
async def list_webflow_sites() -> WebflowSitesResult:
    return await webflow_service.list_sites()


@router.get("/collections", response_model=WebflowCollectionsResult)
async def list_webflow_collections(
    site_id: str = Query(...),
) -> WebflowCollectionsResult:
    return await webflow_service.list_collections(site_id=site_id)


@router.get(
    "/collections/{collection_id}/fields",
    response_model=WebflowFieldsResult,
)
async def list_webflow_fields(
    collection_id: str,
) -> WebflowFieldsResult:
    return await webflow_service.list_fields(collection_id=collection_id)


@router.post("/connect", response_model=WebflowStatus)
async def connect_webflow(
    request: WebflowConnectRequest,
) -> WebflowStatus:
    return await webflow_service.connect(request=request)


@router.delete("/disconnect", status_code=204)
async def disconnect_webflow() -> None:
    await webflow_service.disconnect()


@router.post(
    "/projects/{project_id}/publish",
    response_model=WebflowPublishResult,
)
async def publish_project_to_webflow(
    project_id: UUID,
) -> WebflowPublishResult:
    return await webflow_service.publish_project(
        project_id=project_id,
    )


@router.post(
    "/projects/{project_id}/go-live",
    response_model=WebflowPublishResult,
)
async def go_live_on_webflow(
    project_id: UUID,
) -> WebflowPublishResult:
    return await webflow_service.go_live(
        project_id=project_id,
    )
