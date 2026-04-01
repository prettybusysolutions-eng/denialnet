from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool, NullPool, StaticPool
from config import settings

_engine = None
_Session = None


def get_engine():
    global _engine
    if _engine is None:
        db_url = settings.DATABASE_URL or "sqlite:///./denialnet.db"
        if db_url.startswith("sqlite"):
            # SQLite: use NullPool for thread safety, single connection per thread
            _engine = create_engine(
                db_url,
                poolclass=NullPool,
                echo=False,
                connect_args={"check_same_thread": False, "timeout": 30}
            )
        else:
            # PostgreSQL: use QueuePool for production connection reuse
            _engine = create_engine(
                db_url,
                poolclass=QueuePool,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,       # verify connections before checkout
                pool_recycle=3600,        # recycle connections after 1hr
                echo=False,
            )
    return _engine


def get_session():
    global _Session
    if _Session is None:
        _Session = scoped_session(sessionmaker(bind=get_engine()))
    return _Session()


def init_db():
    from models import Base
    engine = get_engine()
    Base.metadata.create_all(engine)
