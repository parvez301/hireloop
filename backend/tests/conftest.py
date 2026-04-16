import getpass
import os
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
import pytest_asyncio
from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

os.environ.setdefault("ENVIRONMENT", "test")

_backend_root = Path(__file__).resolve().parent.parent
_dotenv = _backend_root / ".env"
if _dotenv.exists():
    load_dotenv(_dotenv)

if os.environ.get("TEST_DATABASE_URL"):
    os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
elif not os.environ.get("DATABASE_URL"):
    if os.environ.get("CI") in ("1", "true", "True"):
        os.environ["DATABASE_URL"] = (
            "postgresql+asyncpg://postgres:postgres@localhost:5432/hireloop"
        )
    else:
        _u = getpass.getuser()
        os.environ["DATABASE_URL"] = (
            f"postgresql+asyncpg://{_u}@localhost:5432/hireloop"
        )

os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("COGNITO_USER_POOL_ID", "us-east-1_test")
os.environ.setdefault("COGNITO_CLIENT_ID", "testclient")
os.environ.setdefault("COGNITO_REGION", "us-east-1")
os.environ.setdefault("COGNITO_JWKS_URL", "http://localhost/jwks")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("GOOGLE_API_KEY", "test-google-key")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:5173")
os.environ.setdefault("PDF_RENDER_URL", "http://localhost:4000")
os.environ.setdefault("APP_URL", "http://localhost:5173")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_placeholder")
os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_placeholder")
os.environ.setdefault("STRIPE_PRICE_PRO_MONTHLY", "price_placeholder")
os.environ.setdefault("INNGEST_EVENT_KEY", "")
os.environ.setdefault("INNGEST_SIGNING_KEY", "")
os.environ.setdefault("INNGEST_DEV", "1")
os.environ.setdefault("FEATURE_SCAN_SCHEDULING", "false")
os.environ.setdefault("SCAN_MAX_LISTINGS_PER_RUN", "500")
os.environ.setdefault("SCAN_BOARD_RATE_LIMIT_REQS_PER_SEC", "1")
os.environ.setdefault("SCAN_L1_CONCURRENCY", "5")
os.environ.setdefault("BATCH_L2_CONCURRENCY", "10")
os.environ.setdefault("BATCH_L1_RELEVANCE_THRESHOLD", "0.5")

from hireloop.config import get_settings  # noqa: E402

get_settings.cache_clear()

from hireloop.db import dispose_engine, get_engine, get_session_factory  # noqa: E402
from hireloop.main import app  # noqa: E402

FAKE_CLAIMS = {
    "sub": "cognito-sub-xyz",
    "email": "crud@example.com",
    "custom:role": "user",
    "custom:subscription_tier": "trial",
}

SECOND_USER_CLAIMS = {
    "sub": "cognito-sub-bee",
    "email": "b@example.com",
    "custom:role": "user",
    "custom:subscription_tier": "trial",
}


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer fake"}


async def _verify_token(token: str) -> dict:
    if token == "fake-b":
        return SECOND_USER_CLAIMS
    return FAKE_CLAIMS


@pytest_asyncio.fixture
async def seed_profile() -> None:
    """Committed profile + resume JSON for the primary test user."""
    factory = get_session_factory()
    async with factory() as session:
        from hireloop.models.profile import Profile
        from hireloop.models.user import User

        r = await session.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        user = r.scalar_one_or_none()
        if user is None:
            user = User(
                cognito_sub=FAKE_CLAIMS["sub"],
                email=FAKE_CLAIMS["email"],
                name="Test",
            )
            session.add(user)
            await session.flush()
        pr = await session.execute(select(Profile).where(Profile.user_id == user.id))
        profile = pr.scalar_one_or_none()
        if profile is None:
            profile = Profile(user_id=user.id, onboarding_state="done")
            session.add(profile)
        profile.parsed_resume_json = {
            "skills": ["python", "fastapi", "postgres", "kubernetes"],
            "total_years_experience": 6,
        }
        profile.target_locations = ["remote", "new york"]
        profile.min_salary = 140000
        profile.master_resume_md = (
            "# Jane Doe\n\n## Summary\n\nSoftware engineer with Python and distributed systems."
        )
        await session.commit()


@pytest_asyncio.fixture
async def seed_conversation(seed_profile: None):
    from hireloop.models.conversation import Conversation
    from hireloop.models.user import User

    factory = get_session_factory()
    async with factory() as session:
        ur = await session.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        user = ur.scalar_one()
        conv = Conversation(user_id=user.id, title="Seed chat")
        session.add(conv)
        await session.commit()
        await session.refresh(conv)
        return conv


@pytest_asyncio.fixture
async def second_test_user(seed_profile: None) -> dict:
    """Second user with profile, for cross-user tests."""
    factory = get_session_factory()
    async with factory() as session:
        from hireloop.models.profile import Profile
        from hireloop.models.user import User

        r = await session.execute(select(User).where(User.cognito_sub == SECOND_USER_CLAIMS["sub"]))
        user = r.scalar_one_or_none()
        if user is None:
            user = User(
                cognito_sub=SECOND_USER_CLAIMS["sub"],
                email=SECOND_USER_CLAIMS["email"],
                name="Bee",
            )
            session.add(user)
            await session.flush()
        pr = await session.execute(select(Profile).where(Profile.user_id == user.id))
        profile = pr.scalar_one_or_none()
        if profile is None:
            profile = Profile(user_id=user.id, onboarding_state="done")
            session.add(profile)
        profile.parsed_resume_json = {
            "skills": ["python", "fastapi", "postgres", "kubernetes"],
            "total_years_experience": 6,
        }
        profile.target_locations = ["remote", "new york"]
        profile.min_salary = 140000
        await session.commit()
    return {"headers": {"Authorization": "Bearer fake-b"}}


@pytest.fixture
def random_job_id():
    from uuid import uuid4

    return uuid4()


@pytest_asyncio.fixture
async def seeded_cv_output(seed_profile: None, seeded_evaluation_for_user_a):
    from hireloop.models.cv_output import CvOutput
    from hireloop.models.user import User

    factory = get_session_factory()
    async with factory() as session:
        ur = await session.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        user = ur.scalar_one()
        cv = CvOutput(
            user_id=user.id,
            job_id=seeded_evaluation_for_user_a.job_id,
            tailored_md="v0",
            pdf_s3_key=f"cv-outputs/{user.id}/old.pdf",
            changes_summary="seed",
            model_used="claude-test",
        )
        session.add(cv)
        await session.commit()
        await session.refresh(cv)
        return cv


@pytest_asyncio.fixture
async def seeded_evaluation_for_user_a(seed_profile: None):
    import hashlib
    from uuid import uuid4

    from hireloop.models.evaluation import Evaluation
    from hireloop.models.job import Job
    from hireloop.models.user import User

    factory = get_session_factory()
    async with factory() as session:
        ur = await session.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        user = ur.scalar_one()
        h = hashlib.sha256(str(uuid4()).encode()).hexdigest()
        job = Job(
            content_hash=h,
            title="Seed Job",
            description_md="desc",
            requirements_json={"skills": ["python"]},
            source="manual",
        )
        session.add(job)
        await session.flush()
        dims = {
            "skills_match": {"score": 1.0, "grade": "A", "reasoning": "", "signals": []},
            "experience_fit": {"score": 1.0, "grade": "A", "reasoning": "", "signals": []},
            "location_fit": {"score": 1.0, "grade": "A", "reasoning": "", "signals": []},
            "salary_fit": {"score": 1.0, "grade": "A", "reasoning": "", "signals": []},
            "domain_relevance": {"score": 0.8, "grade": "B", "reasoning": "", "signals": []},
            "role_match": {"score": 0.8, "grade": "B", "reasoning": "", "signals": []},
            "trajectory_fit": {"score": 0.8, "grade": "B", "reasoning": "", "signals": []},
            "culture_signal": {"score": 0.8, "grade": "B", "reasoning": "", "signals": []},
            "red_flags": {"score": 0.8, "grade": "B", "reasoning": "", "signals": []},
            "growth_potential": {"score": 0.8, "grade": "B", "reasoning": "", "signals": []},
        }
        ev = Evaluation(
            user_id=user.id,
            job_id=job.id,
            overall_grade="B",
            dimension_scores=dims,
            reasoning="seed",
            match_score=0.75,
            recommendation="worth_exploring",
            model_used="claude-test",
            cached=False,
        )
        session.add(ev)
        await session.commit()
        await session.refresh(ev)
        return ev


@pytest_asyncio.fixture(autouse=True)
async def _fake_redis_dependency() -> AsyncIterator[None]:
    """In-memory Redis so integration tests do not require redis-server."""
    from fakeredis import FakeAsyncRedis

    from hireloop.api.deps import get_redis_client, get_redis_optional

    fake = FakeAsyncRedis(decode_responses=True)

    async def _override() -> FakeAsyncRedis:
        return fake

    async def _override_optional() -> FakeAsyncRedis:
        return fake

    app.dependency_overrides[get_redis_client] = _override
    app.dependency_overrides[get_redis_optional] = _override_optional
    yield
    app.dependency_overrides.pop(get_redis_client, None)
    app.dependency_overrides.pop(get_redis_optional, None)


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    try:
        async with get_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"PostgreSQL not reachable (integration tests need a running DB): {exc}")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncIterator[AsyncSession]:
    engine = get_engine()
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with engine.connect() as conn:
        async with conn.begin() as transaction:
            session = session_factory(bind=conn)
            try:
                yield session
            finally:
                await session.close()
                await transaction.rollback()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _dispose_engine_session() -> AsyncIterator[None]:
    yield
    await dispose_engine()
