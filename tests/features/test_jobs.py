import os
from collections.abc import AsyncIterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from tal.db.base import Base
from tal.db.session import get_db_session
from tal.features.auth.dependencies import get_current_user
from tal.features.auth.entities import User
from tal.features.jobs import service
from tal.features.jobs.providers import (
    BoardSource,
    FetchedFeed,
    FoundJob,
    normalize_jobs,
    parse_board_url,
)
from tal.main import app


def test_internal_scan_rejects_missing_wrong_or_jwt_secret() -> None:
    jwt_secret = os.environ.get("JWT_SECRET_KEY", "test-jwt-secret")
    with TestClient(app) as client:
        path = "/api/v1/jobs/internal/scan"
        assert client.post(path).status_code == 404
        assert client.post(path, headers={"X-Tal-Scan-Key": "wrong"}).status_code == 404
        assert client.post(path, headers={"X-Tal-Scan-Key": jwt_secret}).status_code == 404


@pytest.mark.parametrize(
    ("url", "provider", "slug"),
    [
        ("https://job-boards.greenhouse.io/acme", "greenhouse", "acme"),
        ("https://jobs.lever.co/acme", "lever", "acme"),
        ("https://jobs.eu.lever.co/acme", "lever-eu", "acme"),
        ("https://jobs.ashbyhq.com/acme", "ashby", "acme"),
    ],
)
def test_supported_public_board_urls(url: str, provider: str, slug: str) -> None:
    source = parse_board_url(url)
    assert (source.provider, source.slug) == (provider, slug)


@pytest.mark.parametrize(
    "url",
    [
        "http://jobs.lever.co/acme",
        "https://jobs.lever.co@127.0.0.1/acme",
        "https://127.0.0.1/acme",
        "https://jobs.ashbyhq.com/acme/other",
        "https://jobs.ashbyhq.com/acme?next=https://example.org",
        "https://jobs.lever.co/acme%2Fother",
    ],
)
def test_untrusted_board_urls_are_rejected(url: str) -> None:
    with pytest.raises(ValueError):
        parse_board_url(url)


def test_provider_shapes_normalize_without_model() -> None:
    cases = [
        (
            BoardSource("greenhouse", "acme", ""),
            {
                "jobs": [
                    {
                        "id": 1,
                        "title": "Engineer",
                        "absolute_url": "https://job-boards.greenhouse.io/acme/jobs/1",
                        "location": {"name": "Remote"},
                    }
                ]
            },
        ),
        (
            BoardSource("lever", "acme", ""),
            [
                {
                    "id": "2",
                    "text": "Designer",
                    "hostedUrl": "https://jobs.lever.co/acme/2",
                    "categories": {"location": "London"},
                }
            ],
        ),
        (
            BoardSource("ashby", "acme", ""),
            {
                "jobs": [
                    {
                        "id": "3",
                        "title": "Manager",
                        "jobUrl": "https://jobs.ashbyhq.com/acme/3",
                        "location": "Berlin",
                    }
                ]
            },
        ),
    ]
    for source, payload in cases:
        jobs = normalize_jobs(source, payload)
        assert len(jobs) == 1
        assert jobs[0].title
        assert jobs[0].job_url.startswith("https://")


@pytest.mark.asyncio
async def test_scan_upserts_closes_and_isolates_users(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with sessions() as session:
        owner = User(email="jobs-owner@example.com")
        stranger = User(email="jobs-stranger@example.com")
        session.add_all([owner, stranger])
        await session.commit()
        await session.refresh(owner)
        await session.refresh(stranger)

    async def db() -> AsyncIterator[AsyncSession]:
        async with sessions() as session:
            yield session

    current = owner

    async def current_user() -> User:
        return current

    calls = 0

    async def feed(_: BoardSource) -> FetchedFeed:
        nonlocal calls
        calls += 1
        if calls <= 2:
            return FetchedFeed(
                [
                    FoundJob(
                        "job-1",
                        "Backend Engineer",
                        "Remote",
                        "Remote",
                        "Full-time",
                        "Build services",
                        "https://jobs.lever.co/acme/job-1",
                        "https://jobs.lever.co/acme/job-1",
                    )
                ],
                b"snapshot",
            )
        return FetchedFeed([], b"empty")

    monkeypatch.setattr(service, "fetch_jobs", feed)
    app.dependency_overrides[get_db_session] = db
    app.dependency_overrides[get_current_user] = current_user
    try:
        with TestClient(app) as client:
            assert (
                client.post(
                    "/api/v1/jobs/boards", json={"board_url": "https://jobs.lever.co/acme"}
                ).status_code
                == 201
            )
            assert (
                client.post(
                    "/api/v1/jobs/boards", json={"board_url": "https://jobs.lever.co/acme"}
                ).status_code
                == 201
            )
            assert len(client.get("/api/v1/jobs/boards").json()) == 1
            first = client.post("/api/v1/jobs/scan").json()
            assert first[0]["status"] == "success"
            assert len(client.get("/api/v1/jobs").json()) == 1
            assert client.get("/api/v1/jobs?query=designer").json() == []
            current = stranger
            assert client.get("/api/v1/jobs").json() == []
            current = owner
            async with sessions() as session:
                board = (await service.list_watches(session, owner.id))[0]
                await service.scan_board(session, board, force=True)
                assert len(await service.list_jobs(session, owner.id)) == 1
                await service.scan_board(session, board, force=True)
            assert client.get("/api/v1/jobs").json() == []
            closed = client.get("/api/v1/jobs?live_only=false").json()
            assert len(closed) == 1 and closed[0]["is_live"] is False
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


@pytest.mark.asyncio
async def test_failed_feed_does_not_close_existing_jobs(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with sessions() as session:
        user = User(email="jobs-failure@example.com")
        session.add(user)
        await session.commit()
        await session.refresh(user)
        board = await service.watch_board(session, user.id, "https://jobs.ashbyhq.com/acme")

        async def good(_: BoardSource) -> FetchedFeed:
            return FetchedFeed(
                [
                    FoundJob(
                        "1",
                        "Engineer",
                        None,
                        None,
                        None,
                        None,
                        "https://jobs.ashbyhq.com/acme/1",
                        "https://jobs.ashbyhq.com/acme/1",
                    )
                ],
                b"snapshot",
            )

        async def bad(_: BoardSource) -> FetchedFeed:
            raise ValueError("provider unavailable")

        monkeypatch.setattr(service, "fetch_jobs", good)
        await service.scan_board(session, board, force=True)
        monkeypatch.setattr(service, "fetch_jobs", bad)
        result = await service.scan_board(session, board, force=True)
        assert result.status == "failed"
        assert len(await service.list_jobs(session, user.id)) == 1
    await engine.dispose()


@pytest.mark.asyncio
async def test_public_catalog_is_visible_without_a_watch_and_pages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with sessions() as session:
        user = User(email="public-jobs@example.com")
        session.add(user)
        await session.commit()
        await session.refresh(user)

    async def db() -> AsyncIterator[AsyncSession]:
        async with sessions() as session:
            yield session

    async def current_user() -> User:
        return user

    async def feed(_: BoardSource) -> FetchedFeed:
        return FetchedFeed(
            [
                FoundJob(
                    str(index),
                    f"Engineer {index}",
                    "Remote - India",
                    "Remote",
                    "Full-time",
                    None,
                    f"https://job-boards.greenhouse.io/testco/jobs/{index}",
                    f"https://job-boards.greenhouse.io/testco/jobs/{index}",
                )
                for index in range(55)
            ],
            b"snapshot",
        )

    monkeypatch.setattr(
        service, "CATALOG_BOARDS", (("https://job-boards.greenhouse.io/testco", "Test Co"),)
    )
    monkeypatch.setattr(service, "fetch_jobs", feed)
    app.dependency_overrides[get_db_session] = db
    app.dependency_overrides[get_current_user] = current_user
    try:
        async with sessions() as session:
            scans = await service.scan_all_boards(session)
            assert len(scans) == 1 and scans[0].found_count == 55
            assert len(await service.list_jobs(session, user.id, offset=50)) == 5
            await service.ensure_catalog(session)
            assert len(await service.list_catalog(session)) == 1
        with TestClient(app) as client:
            assert client.get("/api/v1/jobs/boards").json() == []
            assert client.get("/api/v1/jobs/catalog").json()[0]["company_name"] == "Test Co"
            assert len(client.get("/api/v1/jobs").json()) == 51
            assert len(client.get("/api/v1/jobs?offset=50").json()) == 5
            assert len(client.get("/api/v1/jobs?location=India").json()) == 51
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()
