import os


# Every app.* import eventually pulls in app.core.config.settings,
# which requires these fields with no defaults. Set harmless dummy
# values before anything under test gets imported, so the suite
# doesn't need a real .env / real secrets to run (e.g. in CI).
# os.environ.setdefault leaves a developer's real local .env-derived
# values alone if pydantic-settings has already surfaced them as
# process env vars; nothing here makes a real network or DB call.
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault(
    "SUPABASE_DB_URL",
    "postgresql://test:test@localhost:5432/test",
)
os.environ.setdefault(
    "SUPABASE_URL", "https://test.supabase.co"
)
os.environ.setdefault("DEFAULT_SITE_NAME", "Test Site")
os.environ.setdefault(
    "DEFAULT_SITE_URL", "https://example.com"
)
os.environ.setdefault(
    "DEFAULT_AUTHOR_NAME", "Test Author"
)
