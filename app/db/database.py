from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import settings


engine_kwargs = {
    "echo": settings.db_echo,
}

if settings.database_uses_external_pooler:
    engine_kwargs["poolclass"] = NullPool
else:
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_size"] = (
        settings.db_pool_size
    )
    engine_kwargs["max_overflow"] = (
        settings.db_max_overflow
    )

engine = create_async_engine(
    settings.database_url,
    **engine_kwargs,
)


AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db_session() -> (
    AsyncGenerator[AsyncSession, None]
):
    async with AsyncSessionFactory() as session:
        yield session
