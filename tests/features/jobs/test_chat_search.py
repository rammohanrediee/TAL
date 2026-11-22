from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tal.db.base import Base
from tal.features.auth.entities import User
from tal.features.jobs.chat_search import ChatSearchFilters, chat_search_jobs
from tal.features.jobs.entities import JobBoard, JobPosting
from tal.features.matching.fit import MIN_DESCRIPTION_CHARS
from tal.features.resumes.entities import Resume, ResumeEvidence, ResumeTextBlock
from tal.features.resumes.models import EvidenceStatus, EvidenceType, ResumeStatus


@pytest.mark.asyncio
async def test_chat_search_ranks_higher_fit_first() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    now = datetime.now(UTC)
    async with sessions() as session:
        user = User(email="searcher@example.com")
        session.add(user)
        await session.flush()

        resume = Resume(
            user_id=user.id,
            original_filename="resume.pdf",
            content_type="application/pdf",
            size_bytes=100,
            storage_key="users/test/resumes/search.pdf",
            sha256="a" * 64,
            status=ResumeStatus.READY,
        )
        session.add(resume)
        await session.flush()

        block = ResumeTextBlock(
            resume_id=resume.id,
            ordinal=1,
            text="Python FastAPI PostgreSQL",
        )
        session.add(block)
        await session.flush()

        for label in ("Python", "FastAPI", "PostgreSQL"):
            session.add(
                ResumeEvidence(
                    resume_id=resume.id,
                    source_block_id=block.id,
                    evidence_type=EvidenceType.SKILL,
                    status=EvidenceStatus.CONFIRMED,
                    extracted_text=label,
                    source_text=label,
                    confidence=0.9,
                    canonical_skill_name=label,
                )
            )

        board = JobBoard(
            provider="greenhouse",
            slug="acme",
            company_name="Acme",
            board_url="https://job-boards.greenhouse.io/acme",
            is_catalog=True,
            last_scanned_at=now,
        )
        session.add(board)
        await session.flush()
        strong = JobPosting(
            board_id=board.id,
            external_id="1",
            title="Python Backend Engineer",
            description=("Python FastAPI PostgreSQL " * 20)[: MIN_DESCRIPTION_CHARS + 50],
            job_url="https://example.com/1",
            apply_url="https://example.com/1",
            is_live=True,
            first_seen_at=now,
            last_seen_at=now,
            last_verified_at=now,
        )
        weak = JobPosting(
            board_id=board.id,
            external_id="2",
            title="Graphic Designer",
            description=("Design Figma illustrations " * 20)[: MIN_DESCRIPTION_CHARS + 50],
            job_url="https://example.com/2",
            apply_url="https://example.com/2",
            is_live=True,
            first_seen_at=now,
            last_seen_at=now,
            last_verified_at=now,
        )
        session.add_all([strong, weak])
        await session.commit()

        result = await chat_search_jobs(
            session,
            user.id,
            conversation_id=None,
            filters=ChatSearchFilters(),
        )
        assert len(result.jobs) == 2
        assert result.jobs[0].title == "Python Backend Engineer"
        assert result.jobs[0].fit_score is not None
        assert (result.jobs[1].fit_score or 0) <= (result.jobs[0].fit_score or 0)


@pytest.mark.asyncio
async def test_chat_search_filters_query_text() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    user = User(email="filter@example.com")
    now = datetime.now(UTC)
    async with sessions() as session:
        session.add(user)
        await session.flush()
        board = JobBoard(
            provider="greenhouse",
            slug="acme",
            company_name="Acme",
            board_url="https://job-boards.greenhouse.io/acme",
            is_catalog=True,
            last_scanned_at=now,
        )
        session.add(board)
        await session.flush()
        session.add(
            JobPosting(
                board_id=board.id,
                external_id="1",
                title="Python Backend Engineer",
                description=("Python " * 50)[: MIN_DESCRIPTION_CHARS + 20],
                job_url="https://example.com/1",
                apply_url="https://example.com/1",
                is_live=True,
                first_seen_at=now,
                last_seen_at=now,
                last_verified_at=now,
            )
        )
        session.add(
            JobPosting(
                board_id=board.id,
                external_id="2",
                title="Graphic Designer",
                description=("Design " * 50)[: MIN_DESCRIPTION_CHARS + 20],
                job_url="https://example.com/2",
                apply_url="https://example.com/2",
                is_live=True,
                first_seen_at=now,
                last_seen_at=now,
                last_verified_at=now,
            )
        )
        await session.commit()

        result = await chat_search_jobs(
            session,
            user.id,
            conversation_id=None,
            filters=ChatSearchFilters(query="Python"),
        )
        assert len(result.jobs) == 1
        assert result.jobs[0].title == "Python Backend Engineer"