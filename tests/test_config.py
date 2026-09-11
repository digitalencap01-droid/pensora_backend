from app.core.config import Settings


def test_normalize_database_url_rewrites_postgres_scheme():
    result = Settings._normalize_database_url(
        "postgres://user:pass@host:5432/db"
    )

    assert result.startswith(
        "postgresql+psycopg://user:pass@host:5432/db"
    )


def test_normalize_database_url_rewrites_postgresql_scheme():
    result = Settings._normalize_database_url(
        "postgresql://user:pass@host:5432/db"
    )

    assert result.startswith(
        "postgresql+psycopg://user:pass@host:5432/db"
    )


def test_normalize_database_url_forces_sslmode_for_supabase_hosts():
    result = Settings._normalize_database_url(
        "postgresql://user:pass@db.project.supabase.co:5432/postgres"
    )

    assert "sslmode=require" in result


def test_normalize_database_url_leaves_non_supabase_hosts_alone():
    result = Settings._normalize_database_url(
        "postgresql://user:pass@localhost:5432/db"
    )

    assert "sslmode" not in result


def test_normalize_database_url_does_not_double_encode_password():
    result = Settings._normalize_database_url(
        "postgresql://user:p%40ss@host:5432/db"
    )

    assert "p%40ss" in result
