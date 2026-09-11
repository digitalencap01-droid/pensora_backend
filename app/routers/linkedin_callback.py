from fastapi import Depends, FastAPI, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.database import get_db_session
from app.services.linkedin_service import linkedin_service


# Mounted (not included) from app.main so LinkedIn can redirect the
# user's browser here directly. Auth comes from the signed `state`
# param minted by GET /api/v1/linkedin/connect (see
# linkedin_service._sign_state) — not from a bearer token.
callback_app = FastAPI()


@callback_app.get("/callback")
async def linkedin_oauth_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> RedirectResponse:
    frontend_url = settings.frontend_url.rstrip("/")

    if error or not code or not state:
        return RedirectResponse(
            f"{frontend_url}/library?linkedin=error"
        )

    try:
        return_path = await linkedin_service.handle_callback(
            session=session,
            code=code,
            state=state,
        )
    except Exception:
        return RedirectResponse(
            f"{frontend_url}/library?linkedin=error"
        )

    separator = "&" if "?" in return_path else "?"
    return RedirectResponse(
        f"{frontend_url}{return_path}{separator}linkedin=connected"
    )
