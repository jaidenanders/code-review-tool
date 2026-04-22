import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.models.review import Base

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./dev.db"   # default: local SQLite for dev/tests
)


def make_engine(url: str | None = None):
    target = url or DATABASE_URL
    connect_args = {"check_same_thread": False} if "sqlite" in target else {}
    return create_async_engine(target, connect_args=connect_args, echo=False)


engine = make_engine()

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db(eng=None):
    """Create all tables. Pass a custom engine for tests."""
    target_engine = eng or engine
    async with target_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """FastAPI dependency: yields an AsyncSession."""
    async with AsyncSessionLocal() as session:
        yield session
