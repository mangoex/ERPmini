import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db_session
from app.core.security import TenantContext
from app.core.uuid7 import generate_uuid7
from app.main import create_app


@pytest.fixture
def tenant_context() -> TenantContext:
    """Provides a default valid UUIDv7 multi-tenant context for AgroPlásticos Industriales."""
    return TenantContext(
        tenant_id=generate_uuid7(),
        branch_id=generate_uuid7(),
        user_id=generate_uuid7(),
        roles=["ADMIN_PLANTA"],
        permissions=["*"],
    )


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    """Creates an isolated in-memory SQLite database with PRAGMA foreign_keys=ON per test."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def client(
    db_session: AsyncSession, tenant_context: TenantContext
) -> AsyncClient:
    """Provides an httpx AsyncClient wired to the FastAPI app with overridden DB session."""
    app = create_app()

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db_session] = _override_get_db

    transport = ASGITransport(app=app)
    headers = {
        "X-Tenant-Id": str(tenant_context.tenant_id),
        "X-Branch-Id": str(tenant_context.branch_id),
        "X-User-Id": str(tenant_context.user_id),
        "X-User-Roles": ",".join(tenant_context.roles),
    }
    async with AsyncClient(
        transport=transport, base_url="http://testserver", headers=headers
    ) as ac:
        yield ac
