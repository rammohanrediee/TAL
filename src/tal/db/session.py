from collections.abc import AsyncIterator

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from tal.core.config import settings


def async_engine_options(database_url: str) -> tuple[str, dict[str, object]]:
    """Adapt Neon's standard Postgres URL to TAL's asyncpg driver."""
    url = make_url(database_url)
    if url.get_backend_name() != "postgresql":
        return database_url, {}

    query = dict(url.query)
    sslmode = query.pop("sslmode", None)
    query.pop("channel_binding", None)
    url = url.set(drivername="postgresql+asyncpg", query=query)
    connect_args: dict[str, object] = {"ssl": True} if sslmode and sslmode != "disable" else {}
    return url.render_as_string(hide_password=False), connect_args


database_url, connect_args = async_engine_options(settings.database_url)
engine = create_async_engine(database_url, pool_pre_ping=True, connect_args=connect_args)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        yield session
