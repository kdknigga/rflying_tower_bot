"""Keep track of action history."""

import datetime
import logging

from sqlalchemy import DateTime, String, func, insert, select
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, mapped_column


class Base(AsyncAttrs, DeclarativeBase):  # noqa: D101
    pass


class HistoryTable(Base):
    """Represents a table for storing action history."""

    __tablename__ = "history"

    url = mapped_column(String, primary_key=True)
    action = mapped_column(String, primary_key=True)
    time = mapped_column(DateTime)


class History:
    """Keep track of action history."""

    def __init__(
        self, db_connection_string: str = "sqlite+aiosqlite:///:memory:"
    ) -> None:
        """
        Initialize the History class.

        Args:
        ----
            db_connection_string (str, optional): The database connection string. Defaults to "sqlite+aiosqlite:///:memory:".

        """
        self.log: logging.Logger = logging.getLogger(
            f"{__name__}.{self.__class__.__name__}"
        )

        self.db = create_async_engine(db_connection_string, echo=False)

    async def initialize_db(self) -> None:
        """Initialize the database."""
        self.log.info("Initializing database: %s", self.db.url)
        async with self.db.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def check(self, url: str, action: str) -> int:
        """
        Check the number of occurrences of a specific action for a given URL.

        Args:
        ----
            url (str): The URL to check.
            action (str): The action to check.

        Returns:
        -------
            int: The number of occurrences of the action for the URL.

        """
        async_session = async_sessionmaker(self.db, expire_on_commit=False)
        # pyrefly: ignore  # bad-argument-type
        async with async_session() as session:
            stmt = (
                select(func.count(HistoryTable.url))
                .where(HistoryTable.url == url)
                .where(HistoryTable.action == action)
            )
            # pyrefly: ignore  # missing-attribute
            n = await session.scalar(stmt)
            if n is not None:
                return n
            return 0

    async def add(self, url: str, action: str) -> None:
        """
        Add a new entry to the history.

        Args:
        ----
            url (str): The URL to add.
            action (str): The action to add.

        Returns:
        -------
            None

        """
        self.log.debug('Inserting url "%s" into history', url)
        async_session = async_sessionmaker(self.db, expire_on_commit=False)
        # pyrefly: ignore  # bad-argument-type
        async with async_session() as session:
            stmt = insert(HistoryTable).values(
                url=url, action=action, time=datetime.datetime.now()
            )
            # pyrefly: ignore  # missing-attribute
            await session.execute(stmt)
            # pyrefly: ignore  # missing-attribute
            await session.commit()
