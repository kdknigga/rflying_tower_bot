"""Tests for the inbox module."""

import asyncio
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from rflying_tower_bot.config import BotConfig
from rflying_tower_bot.inbox import Inbox


class TestInbox:
    """Test the Inbox class."""

    def test_init(self):
        """Test Inbox initialization."""
        mock_config = Mock(spec=BotConfig)
        inbox = Inbox(mock_config)
        
        assert inbox.config == mock_config
        assert inbox.utilities is not None

    @pytest.mark.asyncio
    async def test_do_dump_current_config(self):
        """Test do_dump_current_config static method."""
        mock_subreddit = AsyncMock()
        test_path = Path("/tmp/test_config.yaml")
        
        with patch("rflying_tower_bot.inbox.dump_current_settings") as mock_dump:
            await Inbox.do_dump_current_config(mock_subreddit, test_path)
            mock_dump.assert_called_once_with(mock_subreddit, str(test_path))

    @pytest.mark.asyncio
    async def test_watch_inbox_basic_functionality(self):
        """Test basic watch_inbox functionality that covers main code paths."""
        mock_config = Mock(spec=BotConfig)
        mock_config.reddit = AsyncMock()
        mock_config.subreddit_name = "test_subreddit"
        
        # Mock rules with inbox actions enabled
        mock_rules = Mock()
        mock_general_settings = Mock()
        mock_general_settings.enable_inbox_actions = True
        mock_rules.general_settings = mock_general_settings
        mock_config.rules = mock_rules
        mock_config.update_rules = AsyncMock()
        
        mock_subreddit = AsyncMock()
        mock_config.reddit.subreddit.return_value = mock_subreddit
        
        # Mock moderators with proper async iteration
        mock_mod = Mock()
        mock_mod.name = "test_moderator"
        
        async def mock_moderator_iter():
            yield mock_mod
        
        mock_subreddit.moderator.__aiter__ = mock_moderator_iter
        
        # Create different types of messages to test various command paths
        mock_reload_message = AsyncMock()
        mock_reload_message.author = mock_mod
        mock_reload_message.subject = "reload_config"
        
        mock_dump_message = AsyncMock()
        mock_dump_message.author = mock_mod
        mock_dump_message.subject = "dump_current_config"
        mock_dump_message.body = "/tmp/test_config.yaml"
        
        mock_exit_message = AsyncMock()
        mock_exit_message.author = mock_mod
        mock_exit_message.subject = "exit"
        
        mock_unknown_message = Mock()
        mock_unknown_message.author = mock_mod
        mock_unknown_message.subject = "unknown_command"
        
        mock_non_mod_message = Mock()
        mock_non_mod_message.author = "non_moderator"
        mock_non_mod_message.subject = "test"
        
        # Mock inbox stream with different messages and final None for pause
        async def mock_inbox_stream(**kwargs):
            messages = [
                mock_reload_message,
                mock_dump_message,
                mock_unknown_message,
                mock_non_mod_message,
                None  # Causes pause_after break
            ]
            for message in messages:
                yield message
                
        mock_config.reddit.inbox.stream = mock_inbox_stream
        
        inbox = Inbox(mock_config)
        
        # Mock the do_dump_current_config method
        with patch.object(inbox, 'do_dump_current_config') as mock_dump_method:
            stop_event = asyncio.Event()
            
            # Run one iteration and then stop
            task = asyncio.create_task(inbox.watch_inbox(stop_event))
            await asyncio.sleep(0.01)  # Let it process some messages
            stop_event.set()
            await task
            
            # Verify that reload_config was called
            mock_config.update_rules.assert_called()
            mock_reload_message.mark_read.assert_called()
            
            # Verify that dump_current_config was called  
            mock_dump_method.assert_called_with(mock_subreddit, mock_dump_message.body)
            mock_dump_message.mark_read.assert_called()

    @pytest.mark.asyncio
    async def test_watch_inbox_exit_command(self):
        """Test watch_inbox with exit command."""
        mock_config = Mock(spec=BotConfig)
        mock_config.reddit = AsyncMock()
        mock_config.subreddit_name = "test_subreddit"
        
        # Mock rules with inbox actions enabled
        mock_rules = Mock()
        mock_general_settings = Mock()
        mock_general_settings.enable_inbox_actions = True
        mock_rules.general_settings = mock_general_settings
        mock_config.rules = mock_rules
        
        mock_subreddit = AsyncMock()
        mock_config.reddit.subreddit.return_value = mock_subreddit
        
        # Mock moderators
        mock_mod = Mock()
        
        async def mock_moderator_iter():
            yield mock_mod
        
        mock_subreddit.moderator.__aiter__ = mock_moderator_iter
        
        # Mock exit message
        mock_message = AsyncMock()
        mock_message.author = mock_mod
        mock_message.subject = "exit"
        
        # Mock inbox stream that yields exit message
        async def mock_inbox_stream(**kwargs):
            yield mock_message
                
        mock_config.reddit.inbox.stream = mock_inbox_stream
        
        inbox = Inbox(mock_config)
        stop_event = asyncio.Event()
        
        await inbox.watch_inbox(stop_event)
        
        mock_message.mark_read.assert_called_once()
        assert stop_event.is_set()

    @pytest.mark.asyncio
    async def test_watch_inbox_no_rules(self):
        """Test watch_inbox when rules are not set."""
        mock_config = Mock(spec=BotConfig)
        mock_config.reddit = AsyncMock()
        mock_config.subreddit_name = "test_subreddit"
        mock_config.rules = None
        
        mock_subreddit = AsyncMock()
        mock_config.reddit.subreddit.return_value = mock_subreddit
        
        # Mock moderators
        mock_mod = Mock()
        
        async def mock_moderator_iter():
            yield mock_mod
        
        mock_subreddit.moderator.__aiter__ = mock_moderator_iter
        
        # Mock message from moderator
        mock_message = Mock()
        mock_message.author = mock_mod
        mock_message.subject = "test_command"
        
        # Mock inbox stream
        async def mock_inbox_stream(**kwargs):
            yield mock_message
            yield None  # Causes pause_after break
                
        mock_config.reddit.inbox.stream = mock_inbox_stream
        
        inbox = Inbox(mock_config)
        stop_event = asyncio.Event()
        stop_event.set()  # Set to exit quickly
        
        await inbox.watch_inbox(stop_event)

    @pytest.mark.asyncio
    async def test_watch_inbox_inbox_actions_disabled(self):
        """Test watch_inbox when inbox actions are disabled."""
        mock_config = Mock(spec=BotConfig)
        mock_config.reddit = AsyncMock()
        mock_config.subreddit_name = "test_subreddit"
        
        # Mock rules with inbox actions disabled
        mock_rules = Mock()
        mock_general_settings = Mock()
        mock_general_settings.enable_inbox_actions = False
        mock_rules.general_settings = mock_general_settings
        mock_config.rules = mock_rules
        
        mock_subreddit = AsyncMock()
        mock_config.reddit.subreddit.return_value = mock_subreddit
        
        # Mock moderators
        mock_mod = Mock()
        
        async def mock_moderator_iter():
            yield mock_mod
        
        mock_subreddit.moderator.__aiter__ = mock_moderator_iter
        
        # Mock message from moderator
        mock_message = Mock()
        mock_message.author = mock_mod
        mock_message.subject = "test_command"
        
        # Mock inbox stream
        async def mock_inbox_stream(**kwargs):
            yield mock_message
            yield None  # Causes pause_after break
                
        mock_config.reddit.inbox.stream = mock_inbox_stream
        
        inbox = Inbox(mock_config)
        stop_event = asyncio.Event()
        stop_event.set()  # Set to exit quickly
        
        await inbox.watch_inbox(stop_event)

    @pytest.mark.asyncio
    async def test_watch_inbox_dump_config_error(self):
        """Test watch_inbox when dump_current_config fails."""
        mock_config = Mock(spec=BotConfig)
        mock_config.reddit = AsyncMock()
        mock_config.subreddit_name = "test_subreddit"
        
        # Mock rules with inbox actions enabled
        mock_rules = Mock()
        mock_general_settings = Mock()
        mock_general_settings.enable_inbox_actions = True
        mock_rules.general_settings = mock_general_settings
        mock_config.rules = mock_rules
        
        mock_subreddit = AsyncMock()
        mock_config.reddit.subreddit.return_value = mock_subreddit
        
        # Mock moderators
        mock_mod = Mock()
        
        async def mock_moderator_iter():
            yield mock_mod
        
        mock_subreddit.moderator.__aiter__ = mock_moderator_iter
        
        # Mock dump message
        mock_message = AsyncMock()
        mock_message.author = mock_mod
        mock_message.subject = "dump_current_config"
        mock_message.body = "/tmp/test_config.yaml"
        
        # Mock inbox stream
        async def mock_inbox_stream(**kwargs):
            yield mock_message
            yield None  # Causes pause_after break
                
        mock_config.reddit.inbox.stream = mock_inbox_stream
        
        inbox = Inbox(mock_config)
        
        # Mock the do_dump_current_config method to raise an exception
        with patch.object(inbox, 'do_dump_current_config') as mock_dump_method:
            mock_dump_method.side_effect = Exception("Dump failed")
            
            stop_event = asyncio.Event()
            stop_event.set()  # Set to exit quickly
            
            # Should not raise an exception even though dump fails
            await inbox.watch_inbox(stop_event)
            
            mock_dump_method.assert_called_once()
            mock_message.mark_read.assert_called_once()

    @pytest.mark.asyncio
    async def test_watch_inbox_exception_handling(self):
        """Test watch_inbox exception handling."""
        mock_config = Mock(spec=BotConfig)
        mock_config.reddit = AsyncMock()
        mock_config.subreddit_name = "test_subreddit"
        mock_config.rules = Mock()
        
        mock_subreddit = AsyncMock()
        mock_config.reddit.subreddit.return_value = mock_subreddit
        
        # Mock inbox stream that raises an exception when getting moderators
        async def mock_moderator_iter():
            raise Exception("Moderator fetch failed")
        
        mock_subreddit.moderator.__aiter__ = mock_moderator_iter
        
        inbox = Inbox(mock_config)
        stop_event = asyncio.Event()
        
        # Should handle the exception and set stop_event
        await inbox.watch_inbox(stop_event)
        assert stop_event.is_set()

    @pytest.mark.asyncio 
    async def test_watch_inbox_keyboard_interrupt(self):
        """Test watch_inbox handles KeyboardInterrupt."""
        mock_config = Mock(spec=BotConfig)
        mock_config.reddit = AsyncMock()
        mock_config.subreddit_name = "test_subreddit"
        mock_config.rules = Mock()
        
        mock_subreddit = AsyncMock()
        mock_config.reddit.subreddit.return_value = mock_subreddit
        
        # Mock moderators that raise KeyboardInterrupt
        async def mock_moderator_iter():
            raise KeyboardInterrupt()
        
        mock_subreddit.moderator.__aiter__ = mock_moderator_iter
        
        inbox = Inbox(mock_config)
        stop_event = asyncio.Event()
        
        await inbox.watch_inbox(stop_event)
        assert stop_event.is_set()

    @pytest.mark.asyncio
    async def test_watch_inbox_cancelled_error(self):
        """Test watch_inbox handles CancelledError."""
        mock_config = Mock(spec=BotConfig)
        mock_config.reddit = AsyncMock()
        mock_config.subreddit_name = "test_subreddit"
        mock_config.rules = Mock()
        
        mock_subreddit = AsyncMock()
        mock_config.reddit.subreddit.return_value = mock_subreddit
        
        # Mock moderators that raise CancelledError
        async def mock_moderator_iter():
            raise asyncio.CancelledError()
        
        mock_subreddit.moderator.__aiter__ = mock_moderator_iter
        
        inbox = Inbox(mock_config)
        stop_event = asyncio.Event()
        
        await inbox.watch_inbox(stop_event)
        assert stop_event.is_set()