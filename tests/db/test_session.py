from tal.db.session import async_engine_options


def test_neon_url_uses_asyncpg_and_tls() -> None:
    url, connect_args = async_engine_options(
        "postgresql://user:password@host.example.com/db?sslmode=require&channel_binding=require"
    )

    assert url == "postgresql+asyncpg://user:password@host.example.com/db"
    assert connect_args == {"ssl": True}


def test_sqlite_url_is_unchanged() -> None:
    url, connect_args = async_engine_options("sqlite+aiosqlite:///:memory:")

    assert url == "sqlite+aiosqlite:///:memory:"
    assert connect_args == {}
