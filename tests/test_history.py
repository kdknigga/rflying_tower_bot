"""Tests for the history module."""

import pytest
from unittest.mock import Mock

from rflying_tower_bot.history import Base, History, HistoryTable


class TestBase:
    """Test the Base class."""

    def test_base_exists(self):
        """Test that Base class exists and can be imported."""
        assert Base is not None
        # Base is a DeclarativeBase, so we can't instantiate it directly
        # but we can check that it has the expected attributes
        assert hasattr(Base, 'metadata')


class TestHistoryTable:
    """Test the HistoryTable class."""

    def test_table_name(self):
        """Test that HistoryTable has the correct table name."""
        assert HistoryTable.__tablename__ == "history"

    def test_table_columns(self):
        """Test that HistoryTable has the expected columns."""
        # Check that the columns exist (they're defined as mapped_column)
        assert hasattr(HistoryTable, 'url')
        assert hasattr(HistoryTable, 'action')
        assert hasattr(HistoryTable, 'time')


class TestHistory:
    """Test the History class."""

    def test_init_default_connection_string(self):
        """Test History initialization with default connection string."""
        history = History()
        assert history.db is not None
        assert str(history.db.url) == "sqlite+aiosqlite:///:memory:"

    def test_init_custom_connection_string(self):
        """Test History initialization with custom connection string."""
        custom_connection = "sqlite+aiosqlite:///test.db"
        history = History(custom_connection)
        assert history.db is not None
        assert str(history.db.url) == custom_connection

    @pytest.mark.asyncio
    async def test_initialize_db(self):
        """Test database initialization."""
        history = History("sqlite+aiosqlite:///:memory:")
        
        # This should not raise an exception
        await history.initialize_db()
        
        # Verify the database connection is working
        assert history.db is not None

    @pytest.mark.asyncio
    async def test_check_no_entries(self):
        """Test checking for entries when none exist."""
        history = History("sqlite+aiosqlite:///:memory:")
        await history.initialize_db()
        
        result = await history.check("test_url", "test_action")
        assert result == 0

    @pytest.mark.asyncio
    async def test_check_with_entries(self):
        """Test checking for entries when some exist."""
        history = History("sqlite+aiosqlite:///:memory:")
        await history.initialize_db()
        
        # Add an entry first
        await history.add("test_url", "test_action")
        
        result = await history.check("test_url", "test_action")
        assert result == 1

    @pytest.mark.asyncio
    async def test_check_none_result_scenario(self):
        """Test checking for entries with non-existent combinations."""
        history = History("sqlite+aiosqlite:///:memory:")
        await history.initialize_db()
        
        # Add an entry
        await history.add("test_url", "test_action")
        
        # Check for different URL - should be 0
        result = await history.check("different_url", "test_action")
        assert result == 0
        
        # Check for different action - should be 0
        result = await history.check("test_url", "different_action")
        assert result == 0

    @pytest.mark.asyncio
    async def test_add_entry(self):
        """Test adding a new entry to history."""
        history = History("sqlite+aiosqlite:///:memory:")
        await history.initialize_db()
        
        # This should not raise an exception
        await history.add("test_url", "test_action")
        
        # Verify the entry was added
        count = await history.check("test_url", "test_action")
        assert count == 1

    @pytest.mark.asyncio
    async def test_add_entry_with_special_characters(self):
        """Test adding entry with special characters in URL and action."""
        history = History("sqlite+aiosqlite:///:memory:")
        await history.initialize_db()
        
        url = "https://reddit.com/r/test/comments/123/test-post/?param=value"
        action = "special_action_with_underscores"
        
        # This should not raise an exception
        await history.add(url, action)
        
        # Verify the entry was added
        count = await history.check(url, action)
        assert count == 1

    @pytest.mark.asyncio
    async def test_add_duplicate_entry(self):
        """Test that adding duplicate entry is handled correctly."""
        history = History("sqlite+aiosqlite:///:memory:")
        await history.initialize_db()
        
        url = "test_url"
        action = "test_action"
        
        # Add first entry
        await history.add(url, action)
        count = await history.check(url, action)
        assert count == 1
        
        # Try to add the same entry again - should fail due to primary key constraint
        # but we'll catch and ignore the error in a real scenario
        try:
            await history.add(url, action)
        except Exception:
            # Expected due to primary key constraint
            pass
        
        # Count should still be 1 since duplicate wasn't added
        count = await history.check(url, action)
        assert count == 1

    @pytest.mark.asyncio
    async def test_integration_with_real_memory_db(self):
        """Test actual database operations with in-memory database."""
        # Create a new History instance for this test to avoid conflicts
        history = History("sqlite+aiosqlite:///:memory:")
        
        # Initialize the database
        await history.initialize_db()
        
        # Test adding and checking entries
        url = "https://reddit.com/test/unique"
        action = "test_action_unique"
        
        # Initially should be 0
        count = await history.check(url, action)
        assert count == 0
        
        # Add an entry - this inserts a new row
        await history.add(url, action)
        
        # Now should be 1
        count = await history.check(url, action)
        assert count == 1
        
        # Note: Since the table has composite primary key (url, action),
        # we can't insert the same combination again. The design allows
        # for counting how many times an action was attempted on a URL.
        # Let's test different combinations:
        
        # Check different action should be 0
        count = await history.check(url, "different_action")
        assert count == 0
        
        # Check different URL should be 0
        count = await history.check("https://reddit.com/other/unique", action)
        assert count == 0
        
        # Add entry with different URL
        await history.add("https://reddit.com/other/unique", action)
        count = await history.check("https://reddit.com/other/unique", action)
        assert count == 1
        
        # Add entry with same URL but different action
        await history.add(url, "different_action")
        count = await history.check(url, "different_action")
        assert count == 1
        
        # Original URL and action should still have count of 1
        count = await history.check(url, action)
        assert count == 1