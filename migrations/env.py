import asyncio
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import (
    async_engine_from_config,
)

from app.core.config import settings
from app.db.base import Base
from app.db import models  # noqa: F401


config = context.config


if config.config_file_name is not None:
    fileConfig(
        config.config_file_name
    )


database_url = (
    settings
    .migration_database_url
    .replace(
        "%",
        "%%",
    )
)

config.set_main_option(
    "sqlalchemy.url",
    database_url,
)


target_metadata = Base.metadata


def include_name(name, type_, parent_names):
    # This database is shared with other apps and with Supabase's own
    # auth/storage/realtime/vault schemas. Autogenerate must only ever
    # compare against our own schema, or it will propose dropping
    # tables it doesn't own.
    if type_ == "schema":
        return name == settings.db_schema
    return True


def run_migrations_offline() -> None:
    url = config.get_main_option(
        "sqlalchemy.url"
    )

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={
            "paramstyle": "named"
        },
        compare_type=True,
        include_schemas=True,
        include_name=include_name,
        version_table_schema=(
            settings.db_schema
        ),
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(
    connection,
) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        include_schemas=True,
        include_name=include_name,
        version_table_schema=(
            settings.db_schema
        ),
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    configuration = (
        config.get_section(
            config.config_ini_section
        )
        or {}
    )

    connectable = (
        async_engine_from_config(
            configuration,
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )
    )

    async with connectable.connect() as connection:
        await connection.run_sync(
            do_run_migrations
        )

    await connectable.dispose()


def run_migrations_online() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(
            asyncio.WindowsSelectorEventLoopPolicy()
        )

    asyncio.run(
        run_async_migrations()
    )


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
