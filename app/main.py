import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.articles import (
    router as articles_router,
)
from app.routers.content import (
    router as content_router,
)
from app.routers.content_brief import (
    router as content_brief_router,
)
from app.routers.documents import (
    router as documents_router,
)
from app.routers.html import (
    router as html_router,
)
from app.routers.images import (
    router as images_router,
)
from app.routers.keywords import (
    router as keywords_router,
)
from app.routers.linkedin import (
    router as linkedin_router,
)
from app.routers.linkedin_callback import callback_app as linkedin_callback_app
from app.routers.projects import (
    router as projects_router,
)
from app.routers.research import router as research_router
from app.routers.seo import (
    router as seo_router,
)
from app.routers.webflow import (
    router as webflow_router,
)
from app.core.config import settings


logger = logging.getLogger(__name__)


def _warn_if_unsafe_for_deployment() -> None:
    # See SECURITY.md — .env-based plaintext secrets and debug mode
    # are fine for solo local development, not for anything shared.
    # Authentication is also disabled app-wide for now — see
    # app/core/rate_limit.py and README.md.
    if settings.app_env != "development" and settings.debug:
        logger.warning(
            "APP_ENV=%s with DEBUG=true — disable debug mode "
            "outside local development.",
            settings.app_env,
        )

    if settings.app_env != "development":
        logger.warning(
            "Running with APP_ENV=%s. Confirm secrets are coming "
            "from a real secrets manager, not a checked-in .env "
            "file — see SECURITY.md.",
            settings.app_env,
        )


_warn_if_unsafe_for_deployment()


app = FastAPI(
    title=settings.app_name,
    description=(
        "AI-powered research, SEO, article writing "
        "and publishing platform."
    ),
    version="0.1.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(content_router)
app.include_router(documents_router)
app.include_router(images_router)
app.include_router(projects_router)
app.include_router(research_router)
app.include_router(keywords_router)
app.include_router(content_brief_router)
app.include_router(articles_router)
app.include_router(seo_router)
app.include_router(html_router)
app.include_router(linkedin_router)
app.include_router(webflow_router)

# Mounted as a sub-app (not include_router) — see
# app/routers/linkedin_callback.py.
app.mount("/linkedin", linkedin_callback_app)


@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    return {"status": "ok"}
