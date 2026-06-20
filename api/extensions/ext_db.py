from contextvars import ContextVar, Token

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from config.settings import settings

db_engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,
    pool_size=settings.MYSQL_POOL_SIZE,
    max_overflow=settings.MYSQL_MAX_OVERFLOW_SIZE,
    pool_recycle=settings.MYSQL_POOL_RECYCLE,
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(
    bind=db_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

context_db_session: ContextVar[AsyncSession] = ContextVar("db_session")


class FastapiDB:
    """FastAPI 数据库扩展类,自动管理数据库连接池"""

    @property
    def session(self) -> AsyncSession:
        """ "获取数据库会话"""
        session = context_db_session.get(None)
        if session is None:
            session = async_session_factory()
            context_db_session.set(session)
        return session

    def set_session(self, session: AsyncSession) -> Token:
        """设置数据库会话"""
        token = context_db_session.set(session)
        return token

    def reset_session(self, token: Token) -> None:
        """重置数据库会话"""
        context_db_session.reset(token)


db = FastapiDB()
