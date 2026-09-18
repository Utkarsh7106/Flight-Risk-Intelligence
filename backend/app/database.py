from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """Yields a session scoped to one request/transaction.

    Committed on clean exit, rolled back on exception. RLS session
    variables (app.current_role / app.current_bu_id) are set with
    SET LOCAL inside this same transaction by security/deps.py once the
    caller is authenticated, so they never leak across requests.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
