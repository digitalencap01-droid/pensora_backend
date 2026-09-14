from functools import lru_cache
from urllib.parse import (
    parse_qsl,
    urlencode,
    urlsplit,
    urlunsplit,
)

from pydantic import SecretStr
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


class Settings(BaseSettings):
    # -----------------------
    # Application
    # -----------------------

    app_name: str = "Pensora Backend"
    app_env: str = "development"
    debug: bool = True

    # Comma-separated list of origins allowed to call this API from a
    # browser (the React/Vite frontend). Needed for CORS preflight
    # (OPTIONS) requests to succeed — without it, the browser blocks
    # every request that carries an Authorization header.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # -----------------------
    # OpenAI
    # -----------------------

    openai_api_key: SecretStr
    openai_model: str = "gpt-4.1-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    # -----------------------
    # Document RAG (upload -> chunk -> embed -> ground article)
    # -----------------------

    # Service role key (Project Settings -> API -> service_role, secret).
    # This app talks to Postgres exclusively through Supabase's REST API
    # (PostgREST) — see app/db/supabase_rest.py — rather than a direct
    # database connection, so this key is required for EVERY read/write,
    # not just Storage uploads. It bypasses Row-Level Security the same
    # way a direct superuser connection would.
    supabase_service_role_key: str | None = None
    document_storage_bucket: str = "documents"
    document_max_file_size_mb: int = 20

    # Images extracted from an uploaded document (e.g. figures in a
    # PDF) go in a SEPARATE, public bucket — unlike the source
    # document, these become permanent inline article images/Open
    # Graph images, so they need stable, crawlable public URLs.
    document_images_bucket: str = "document-images"
    document_image_max_count: int = 40
    document_image_min_dimension_px: int = 80

    # -----------------------
    # Direct image upload (generate a blog straight from photos,
    # using vision analysis instead of RAG over a document)
    # -----------------------

    # Reuses document_images_bucket — same public-URL requirement.
    image_batch_max_count: int = 20
    image_max_file_size_mb: int = 10

    # -----------------------
    # Rate limiting
    # -----------------------

    # Each /content/generate call runs several OpenAI calls
    # (parallel web_search + multiple responses.parse), so it's real
    # spend per request — cap how often one user can trigger it.
    generate_rate_limit_count: int = 5
    generate_rate_limit_window_seconds: int = 3600

    # -----------------------
    # Error monitoring
    # -----------------------

    sentry_dsn: str | None = None

    # -----------------------
    # LinkedIn publishing
    # -----------------------

    # "Sign In with LinkedIn using OpenID Connect" + "Share on LinkedIn"
    # products on the app, scopes: openid profile email w_member_social.
    # Leave any of these blank to disable the feature — endpoints return
    # 503 rather than crashing the app on startup.
    linkedin_client_id: str | None = None
    linkedin_client_secret: SecretStr | None = None
    linkedin_redirect_uri: str | None = None
    # Signs the OAuth `state` param (CSRF + carries return_path across
    # the redirect to LinkedIn and back).
    linkedin_state_secret: SecretStr | None = None
    # Fernet key (Fernet.generate_key()) — encrypts stored access/refresh
    # tokens at rest.
    linkedin_token_encryption_key: SecretStr | None = None

    # Where the LinkedIn OAuth callback sends the browser back to.
    frontend_url: str = "http://localhost:5173"

    # -----------------------
    # Webflow publishing
    # -----------------------

    # A single site-level API token (Data API v2, generated in Webflow
    # site settings) shared by every user of this app — unlike
    # LinkedIn, this isn't a per-user OAuth connection. The site and
    # CMS collection to publish into are configured separately at
    # runtime (see WebflowConfig / app/services/webflow_service.py).
    # Leave blank to disable the feature — endpoints return 503.
    webflow_token: SecretStr | None = None

    # -----------------------
    # Database
    # -----------------------

    # The app reads/writes Postgres exclusively through Supabase's REST
    # API (`{supabase_url}/rest/v1`, see app/db/supabase_rest.py) using
    # supabase_service_role_key above — not a direct Postgres
    # connection. supabase_url is also used to build public storage
    # URLs for uploaded documents/images.
    supabase_url: str

    # PostgREST only exposes the `public` schema by default (see
    # README.md) — this app's tables live there. Only affects
    # app/db/base.py's SQLAlchemy metadata (used solely for type
    # definitions in app/db/models.py) and Alembic, both vestigial
    # now that persistence goes through the REST API.
    db_schema: str = "public"

    # Optional — only needed if you run Alembic directly against
    # Postgres yourself (migrations/ is not used by the app at
    # runtime). Leave blank otherwise.
    supabase_db_url: str | None = None
    supabase_migration_db_url: str | None = None

    # -----------------------
    # Pydantic Settings
    # -----------------------

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]

    @property
    def database_url(self) -> str:
        if not self.supabase_db_url:
            raise ValueError(
                "SUPABASE_DB_URL is not set — it's only "
                "needed to run Alembic directly against "
                "Postgres, which the app itself doesn't "
                "require."
            )
        return self._normalize_database_url(
            self.supabase_db_url
        )

    @property
    def migration_database_url(self) -> str:
        raw = (
            self.supabase_migration_db_url
            or self.supabase_db_url
        )
        if not raw:
            raise ValueError(
                "SUPABASE_DB_URL / SUPABASE_MIGRATION_DB_URL "
                "are not set — required only to run Alembic "
                "directly against Postgres."
            )
        return self._normalize_database_url(raw)

    @property
    def database_uses_external_pooler(self) -> bool:
        parsed = urlsplit(self.database_url)
        hostname = parsed.hostname or ""
        return (
            hostname.endswith(
                ".pooler.supabase.com"
            )
            or parsed.port == 6543
        )

    @staticmethod
    def _normalize_database_url(
        raw_url: str,
    ) -> str:
        if raw_url.startswith("postgres://"):
            raw_url = raw_url.replace(
                "postgres://",
                "postgresql+psycopg://",
                1,
            )
        elif raw_url.startswith("postgresql://"):
            raw_url = raw_url.replace(
                "postgresql://",
                "postgresql+psycopg://",
                1,
            )

        parsed = urlsplit(raw_url)
        query = dict(parse_qsl(parsed.query))

        if (
            parsed.hostname
            and "supabase" in parsed.hostname
        ):
            query.setdefault(
                "sslmode",
                "require",
            )

        normalized_query = urlencode(query)

        return urlunsplit(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                normalized_query,
                parsed.fragment,
            )
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
