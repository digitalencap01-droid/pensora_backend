import base64
import hashlib
import hmac
import json
import re
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from uuid import UUID

import httpx
from fastapi import HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.linkedin_repository import linkedin_repository
from app.db.repository import content_repository
from app.db.models import LinkedInConnection
from app.prompts.linkedin import (
    LINKEDIN_ARTICLE_PROMPT,
    LINKEDIN_HASHTAG_PROMPT,
    LINKEDIN_POST_PROMPT,
    LINKEDIN_WEB_SEARCH_ADDENDUM,
)
from app.schemas.document import DocumentResearchRequest
from app.schemas.image_upload import ImageResearchRequest
from app.schemas.linkedin import (
    GeneratedLinkedInContentAI,
    LinkedInContentType,
    LinkedInPublishResult,
    LinkedInStatus,
    SuggestedHashtagsAI,
)
from app.services.crypto import decrypt_token, encrypt_token
from app.services.document_research_service import (
    document_research_service,
)
from app.services.image_research_service import image_research_service
from app.services.openai_service import openai_service


AUTHORIZATION_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
USERINFO_URL = "https://api.linkedin.com/v2/userinfo"
POSTS_URL = "https://api.linkedin.com/rest/posts"

# LinkedIn's versioned REST APIs require this header. LinkedIn cuts a
# new version monthly and keeps each one active for ~12 months, so
# this needs bumping periodically — see
# https://learn.microsoft.com/linkedin/marketing/versioning.
# Confirmed active as of 2026-08.
LINKEDIN_API_VERSION = "202606"

SCOPES = "openid profile email w_member_social"

STATE_TTL_SECONDS = 600


class LinkedInNotConfigured(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=503,
            detail=(
                "LinkedIn publishing isn't configured on this "
                "server yet."
            ),
        )


class LinkedInService:
    _BARE_DOMAIN_PATTERN = re.compile(
        r"(?<!@)\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
        r"(?:com|org|net|io|ai|co|dev|app|in|us|uk|ca|au|tech|me|ly|"
        r"info|biz|cloud|news)\b",
        flags=re.IGNORECASE,
    )

    def _require_config(self) -> None:
        if not (
            settings.linkedin_client_id
            and settings.linkedin_client_secret
            and settings.linkedin_state_secret
            and settings.linkedin_token_encryption_key
        ):
            raise LinkedInNotConfigured()

    def resolve_redirect_uri(
        self,
        request: Request | None = None,
    ) -> str:
        configured = (settings.linkedin_redirect_uri or "").strip()
        if configured:
            return configured

        if request is None:
            raise HTTPException(
                status_code=503,
                detail=(
                    "LinkedIn redirect URI is not configured. Set "
                    "LINKEDIN_REDIRECT_URI or start the OAuth flow "
                    "through this backend directly."
                ),
            )

        return f"{str(request.base_url).rstrip('/')}/linkedin/callback"

    # ---- state (CSRF token that also carries return_path) ----

    def _sign_state(self, payload: dict) -> str:
        secret = (
            settings.linkedin_state_secret.get_secret_value().encode()
        )
        raw = json.dumps(payload, separators=(",", ":")).encode()
        body = base64.urlsafe_b64encode(raw).decode().rstrip("=")
        signature = hmac.new(secret, body.encode(), hashlib.sha256).hexdigest()
        return f"{body}.{signature}"

    def _verify_state(self, state: str) -> dict:
        secret = (
            settings.linkedin_state_secret.get_secret_value().encode()
        )

        try:
            body, signature = state.split(".", 1)
        except ValueError as exc:
            raise HTTPException(
                status_code=400, detail="Malformed state parameter."
            ) from exc

        expected_signature = hmac.new(
            secret, body.encode(), hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_signature):
            raise HTTPException(
                status_code=400, detail="Invalid state parameter."
            )

        padded = body + "=" * (-len(body) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded))

        if payload.get("exp", 0) < time.time():
            raise HTTPException(
                status_code=400,
                detail="LinkedIn connection request expired — try again.",
            )

        return payload

    # ---- OAuth start ----

    def build_authorization_url(
        self,
        return_path: str,
        request: Request | None = None,
    ) -> str:
        self._require_config()
        redirect_uri = self.resolve_redirect_uri(request)

        state = self._sign_state(
            {
                "return_path": return_path,
                "redirect_uri": redirect_uri,
                "exp": time.time() + STATE_TTL_SECONDS,
            }
        )

        params = {
            "response_type": "code",
            "client_id": settings.linkedin_client_id,
            "redirect_uri": redirect_uri,
            "scope": SCOPES,
            "state": state,
        }

        return f"{AUTHORIZATION_URL}?{urlencode(params)}"

    # ---- OAuth callback ----

    async def handle_callback(
        self,
        session: AsyncSession,
        code: str,
        state: str,
    ) -> str:
        """Exchanges the code, stores the connection, and returns the
        frontend return_path the browser should be redirected to."""
        self._require_config()

        payload = self._verify_state(state)
        return_path = payload.get("return_path", "/library")
        redirect_uri = payload.get("redirect_uri") or self.resolve_redirect_uri()

        token_data = await self._exchange_code(
            code,
            redirect_uri=redirect_uri,
        )
        userinfo = await self._fetch_userinfo(token_data["access_token"])

        expires_in = token_data.get("expires_in", 3600)
        token_expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=expires_in
        )

        refresh_token = token_data.get("refresh_token")

        await linkedin_repository.upsert_connection(
            session=session,
            linkedin_member_id=userinfo["sub"],
            linkedin_name=userinfo.get("name"),
            linkedin_email=userinfo.get("email"),
            access_token_encrypted=encrypt_token(
                token_data["access_token"]
            ),
            refresh_token_encrypted=(
                encrypt_token(refresh_token) if refresh_token else None
            ),
            scope=token_data.get("scope", SCOPES),
            token_expires_at=token_expires_at,
        )

        return return_path

    async def _exchange_code(
        self,
        code: str,
        redirect_uri: str,
    ) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": settings.linkedin_client_id,
                    "client_secret": (
                        settings.linkedin_client_secret.get_secret_value()
                    ),
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded"
                },
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=(
                    "LinkedIn rejected the authorization code: "
                    f"{response.text}"
                ),
            )

        return response.json()

    async def _fetch_userinfo(self, access_token: str) -> dict:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail="Could not fetch the LinkedIn profile.",
            )

        return response.json()

    # ---- status / disconnect ----

    async def get_status(
        self,
        session: AsyncSession,
    ) -> LinkedInStatus:
        connection = await linkedin_repository.get_connection(session)

        if connection is None:
            return LinkedInStatus(connected=False)

        return LinkedInStatus(
            connected=True,
            linkedin_name=connection.linkedin_name,
        )

    async def disconnect(
        self,
        session: AsyncSession,
    ) -> None:
        await linkedin_repository.delete_connection(session)

    # ---- generate (Write page: topic -> draft, before publishing) ----

    async def generate_content(
        self,
        session: AsyncSession,
        content_type: LinkedInContentType,
        topic: str,
        tone: str | None,
        use_web_search: bool = False,
        document_id: UUID | None = None,
        image_batch_id: UUID | None = None,
    ) -> str:
        prompt = (
            LINKEDIN_POST_PROMPT
            if content_type == "post"
            else LINKEDIN_ARTICLE_PROMPT
        )

        grounding_context = await self._build_grounding_context(
            session=session,
            topic=topic,
            document_id=document_id,
            image_batch_id=image_batch_id,
        )
        instructions = self._build_generation_instructions(
            base_prompt=prompt,
            grounding_context=grounding_context,
        )
        payload = self._build_generation_payload(
            topic=topic,
            tone=tone,
            grounding_context=grounding_context,
        )

        if use_web_search:
            return await self._generate_with_web_search(
                instructions=(
                    instructions + LINKEDIN_WEB_SEARCH_ADDENDUM
                ),
                input=payload,
            )

        response = await openai_service.client.responses.parse(
            model=openai_service.model,
            instructions=instructions,
            input=payload,
            text_format=GeneratedLinkedInContentAI,
            store=False,
        )

        generated = response.output_parsed

        if generated is None:
            raise HTTPException(
                status_code=502,
                detail="Failed to generate LinkedIn content.",
            )

        return self._sanitize_generated_text(generated.text)

    async def _generate_with_web_search(
        self,
        instructions: str,
        input: str,
    ) -> str:
        # Same "web_search" tool + responses.create pattern as
        # ResearchService._search_web — tool use and structured
        # (.parse) output don't combine, so this returns plain text.
        web_search_tool = {
            "type": "web_search",
            "search_context_size": "medium",
            "external_web_access": True,
        }

        response = await openai_service.client.responses.create(
            model=openai_service.model,
            instructions=instructions,
            tools=[web_search_tool],
            tool_choice="required",
            input=input,
            store=False,
        )

        text = response.output_text.strip()

        if not text:
            raise HTTPException(
                status_code=502,
                detail="Failed to generate LinkedIn content.",
            )

        return self._sanitize_generated_text(text)

    async def _build_grounding_context(
        self,
        session: AsyncSession,
        topic: str,
        document_id: UUID | None,
        image_batch_id: UUID | None,
    ) -> str | None:
        if document_id is not None:
            document = await content_repository.get_document(
                session=session,
                document_id=document_id,
            )
            if document is None:
                raise HTTPException(
                    status_code=404,
                    detail="Uploaded document not found.",
                )

            if document.status != "ready":
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Uploaded document is not ready yet "
                        f"(status: {document.status})."
                    ),
                )

            research = await document_research_service.research(
                session=session,
                document=document,
                request=DocumentResearchRequest(
                    document_id=document.id,
                    topic=topic,
                ),
            )
            return self._summarize_research_context(
                label=f"uploaded document: {document.filename}",
                research=research,
            )

        if image_batch_id is not None:
            batch = await content_repository.get_image_batch(
                session=session,
                batch_id=image_batch_id,
            )
            if batch is None:
                raise HTTPException(
                    status_code=404,
                    detail="Uploaded image batch not found.",
                )

            images = await content_repository.list_batch_images(
                session=session,
                batch_id=batch.id,
            )
            if not images:
                raise HTTPException(
                    status_code=400,
                    detail="Uploaded image batch has no images.",
                )

            research = await image_research_service.research(
                batch=batch,
                images=images,
                request=ImageResearchRequest(
                    batch_id=batch.id,
                    topic=topic,
                ),
            )
            return self._summarize_research_context(
                label="uploaded images",
                research=research,
            )

        return None

    def _build_generation_instructions(
        self,
        base_prompt: str,
        grounding_context: str | None,
    ) -> str:
        if not grounding_context:
            return base_prompt

        return (
            base_prompt
            + "\n\n"
            + "GROUNDING RULES\n\n"
            + "- You will receive grounded research extracted from the "
            + "user's own uploaded material.\n"
            + "- Use that material as the factual basis of the post.\n"
            + "- Do not mention internal source URLs, filenames, page "
            + "numbers, image URLs, or that the content came from an "
            + "upload.\n"
            + "- If the grounded material is thin, stay conservative and "
            + "do not invent unsupported details.\n"
        )

    def _build_generation_payload(
        self,
        topic: str,
        tone: str | None,
        grounding_context: str | None,
    ) -> str:
        payload: dict[str, str] = {
            "topic": topic,
            "tone": tone or "professional",
        }

        if grounding_context:
            payload["grounding_context"] = grounding_context

        return json.dumps(payload, ensure_ascii=False)

    def _summarize_research_context(
        self,
        label: str,
        research,
    ) -> str:
        lines = [
            f"Grounded material: {label}",
            f"Summary: {research.summary}",
        ]

        if research.key_facts:
            lines.append("Key facts:")
            lines.extend(
                f"- {fact.claim}"
                for fact in research.key_facts[:8]
            )

        if research.statistics:
            lines.append("Statistics:")
            lines.extend(
                f"- {fact.claim}"
                for fact in research.statistics[:5]
            )

        if research.important_entities:
            lines.append(
                "Important entities: "
                + ", ".join(research.important_entities[:10])
            )

        if research.content_gaps:
            lines.append("Caveats:")
            lines.extend(
                f"- {gap}"
                for gap in research.content_gaps[:4]
            )

        return "\n".join(lines)

    def _sanitize_generated_text(self, text: str) -> str:
        cleaned = text.strip()

        # Collapse markdown links to their label and strip raw URLs.
        cleaned = re.sub(
            r"\[([^\]]+)\]\((https?://[^)]+)\)",
            r"\1",
            cleaned,
        )
        cleaned = re.sub(r"https?://\S+", "", cleaned)
        cleaned = self._BARE_DOMAIN_PATTERN.sub("", cleaned)

        lines: list[str] = []
        for raw_line in cleaned.splitlines():
            line = raw_line.strip()
            if not line:
                lines.append("")
                continue

            line = re.sub(r"\*\*(.*?)\*\*", r"\1", line)
            line = re.sub(r"__(.*?)__", r"\1", line)
            line = re.sub(r"(?<!\w)[*_](.*?)[*_](?!\w)", r"\1", line)
            line = re.sub(r"^\s*[-*]\s+", "", line)
            line = re.sub(r"^\s*\d+[.)]\s+", "", line)
            line = re.sub(r"\(\s*\)", "", line)
            line = re.sub(r"\s+([,.;:!?])", r"\1", line)
            line = re.sub(r"^[()\[\]\-:;,.\s]+$", "", line)
            line = re.sub(r"\s{2,}", " ", line).strip()

            if line:
                lines.append(line)

        cleaned = "\n".join(lines)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return self._sanitize_for_linkedin_commentary(cleaned)

    def _sanitize_for_linkedin_commentary(
        self,
        text: str,
    ) -> str:
        # LinkedIn commentary uses "little" text formatting for
        # mentions/hashtags. In practice, raw bracket characters can
        # be interpreted as markup and cause the rest of the post to
        # disappear silently, so strip them from plain-text posts.
        cleaned = re.sub(r"[()\[\]{}]", "", text)
        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()

    async def suggest_hashtags(
        self,
        topic: str,
        content_type: LinkedInContentType,
        draft_text: str | None,
    ) -> list[str]:
        response = await openai_service.client.responses.parse(
            model=openai_service.model,
            instructions=LINKEDIN_HASHTAG_PROMPT,
            input=json.dumps(
                {
                    "topic": topic,
                    "content_type": content_type,
                    "draft_text": draft_text,
                },
                ensure_ascii=False,
            ),
            text_format=SuggestedHashtagsAI,
            store=False,
        )

        generated = response.output_parsed

        if generated is None:
            raise HTTPException(
                status_code=502,
                detail="Failed to suggest hashtags.",
            )

        return self._normalize_hashtags(generated.hashtags)

    def _normalize_hashtags(self, hashtags: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []

        for tag in hashtags:
            cleaned = tag.strip().lstrip("#").replace(" ", "")

            if not cleaned:
                continue

            normalized = cleaned.casefold()

            if normalized in seen:
                continue

            seen.add(normalized)
            result.append(f"#{cleaned}")

        return result

    # ---- publish ----

    async def _require_active_connection(
        self,
        session: AsyncSession,
    ) -> LinkedInConnection:
        connection = await linkedin_repository.get_connection(session)

        if connection is None:
            raise HTTPException(
                status_code=400,
                detail="Connect your LinkedIn account first.",
            )

        if connection.token_expires_at <= datetime.now(timezone.utc):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Your LinkedIn connection has expired — "
                    "reconnect your account."
                ),
            )

        return connection

    async def _create_post(
        self,
        access_token: str,
        body: dict,
    ) -> LinkedInPublishResult:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                POSTS_URL,
                json=body,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "LinkedIn-Version": LINKEDIN_API_VERSION,
                    "X-Restli-Protocol-Version": "2.0.0",
                    "Content-Type": "application/json",
                },
            )

        if response.status_code not in (200, 201):
            raise HTTPException(
                status_code=502,
                detail=f"LinkedIn publish failed: {response.text}",
            )

        post_urn = response.headers.get("x-restli-id", "")
        post_url = (
            f"https://www.linkedin.com/feed/update/{post_urn}/"
            if post_urn
            else None
        )

        return LinkedInPublishResult(post_urn=post_urn, post_url=post_url)

    async def publish_article(
        self,
        session: AsyncSession,
        article_title: str,
        article_summary: str,
        article_url: str,
        commentary: str | None,
    ) -> LinkedInPublishResult:
        self._require_config()

        connection = await self._require_active_connection(session)
        access_token = decrypt_token(connection.access_token_encrypted)

        article_content: dict = {
            "source": article_url,
            "title": article_title,
        }

        if article_summary:
            article_content["description"] = article_summary

        body = {
            "author": f"urn:li:person:{connection.linkedin_member_id}",
            "commentary": self._sanitize_for_linkedin_commentary(
                commentary or f"{article_title}\n\n{article_summary}".strip()
            ),
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "content": {"article": article_content},
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }

        return await self._create_post(access_token, body)

    async def publish_post(
        self,
        session: AsyncSession,
        text: str,
    ) -> LinkedInPublishResult:
        """Publishes a plain text post (no link/article preview) —
        used by the Write page's generate-then-approve flow for both
        the "post" and "article" (long-form text) content types."""
        self._require_config()

        connection = await self._require_active_connection(session)
        access_token = decrypt_token(connection.access_token_encrypted)

        body = {
            "author": f"urn:li:person:{connection.linkedin_member_id}",
            "commentary": self._sanitize_for_linkedin_commentary(text),
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }

        return await self._create_post(access_token, body)


linkedin_service = LinkedInService()
