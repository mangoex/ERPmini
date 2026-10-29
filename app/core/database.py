"""Infraestructura de base de datos async con soporte dual PostgreSQL (RLS) y SQLite."""

from collections.abc import AsyncGenerator

from sqlalchemy import event, inspect
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Session

from app.core.config import settings
from app.core.exceptions import ImmutableRecordError


class Base(DeclarativeBase):
    """Base declarativa para todos los modelos de ERPmini."""

    def __getattribute__(self, name: str):
        if name == "id":
            d = object.__getattribute__(self, "__dict__")
            if "id" in d:
                return d["id"]
            try:
                state = object.__getattribute__(self, "_sa_instance_state")
                if state and state.key:
                    pk = state.key[1][0]
                    d["id"] = pk
                    return pk
            except Exception:
                pass
        return super().__getattribute__(name)


# Event listener universal para garantizar inmutabilidad
@event.listens_for(Session, "before_flush")
def _enforce_immutability(session, flush_context, instances):
    for obj in session.dirty:
        if getattr(obj, "__immutable__", False):
            raise ImmutableRecordError(
                f"Record of type {obj.__class__.__name__} is immutable and cannot be updated."
            )
    for obj in session.deleted:
        if getattr(obj, "__immutable__", False):
            raise ImmutableRecordError(
                f"Record of type {obj.__class__.__name__} is immutable and cannot be deleted."
            )


@event.listens_for(Session, "after_rollback")
def _preserve_identities_on_rollback(session):
    for obj in list(session.identity_map.values()):
        try:
            state = inspect(obj)
            if state and state.key:
                obj.__dict__["id"] = state.key[1][0]
        except Exception:
            pass


# Motor y generador de sesiones
engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG, future=True)
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency inyectable de FastAPI para sesiones de BD."""
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
