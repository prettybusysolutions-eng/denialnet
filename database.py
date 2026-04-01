from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import NullPool
from config import settings

_engine = None
_Session = None


def get_engine():
    global _engine
    if _engine is None:
        db_url = settings.DATABASE_URL or "sqlite:///./denialnet.db"
        _engine = create_engine(db_url, poolclass=NullPool, echo=False)
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
