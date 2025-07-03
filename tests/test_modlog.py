"""Tests for the modlog module."""

import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch

from asyncprawcore.exceptions import RequestException, ServerError

from rflying_tower_bot.config import BotConfig
from rflying_tower_bot.modlog import ModLog
from rflying_tower_bot.ruleset_schemas import FlairAction, RemovalReasonSettings


class TestModLog:
    """Test the ModLog class."""

    def test_init(self):
        """Test ModLog initialization."""
        mock_config = Mock(spec=BotConfig)
        modlog = ModLog(mock_config)
        
        assert modlog.config == mock_config
        assert modlog.utilities is not None

    @pytest.mark.asyncio
    async def test_do_action_comment(self):
        """Test do_action_comment method."""
        mock_config = Mock(spec=BotConfig)
        mock_config.subreddit_name = "test_subreddit"
        
        modlog = ModLog(mock_config)
        
        # Mock post and comment
        mock_post = AsyncMock()
        mock_post.author = "test_user"
        mock_post.permalink = "/r/test/comments/123/test"
        
        mock_comment = AsyncMock()
        mock_post.reply.return_value = mock_comment
        
        # Mock utilities.format_comment
        mock_utilities = Mock()
        mock_utilities.format_comment.return_value = "Formatted comment"
        modlog.utilities = mock_utilities
        
        comment_text = "Test comment"
        
        await modlog.do_action_comment(mock_post, comment_text)
        
        mock_utilities.format_comment.assert_called_once_with(comment_text)
        mock_post.reply.assert_called_once_with("Formatted comment")
        mock_comment.mod.distinguish.assert_called_once_with(sticky=True)
        mock_comment.mod.approve.assert_called_once()

    @pytest.mark.asyncio
    async def test_do_action_comment_fails(self):
        """Test do_action_comment when comment creation fails."""
        mock_config = Mock(spec=BotConfig)
        mock_config.subreddit_name = "test_subreddit"
        
        modlog = ModLog(mock_config)
        
        # Mock post that returns None for reply (failure)
        mock_post = AsyncMock()
        mock_post.author = "test_user"
        mock_post.permalink = "/r/test/comments/123/test"
        mock_post.reply.return_value = None
        
        # Mock utilities.format_comment
        mock_utilities = Mock()
        mock_utilities.format_comment.return_value = "Formatted comment"
        modlog.utilities = mock_utilities
        
        comment_text = "Test comment"
        
        # Should not raise an exception even when comment creation fails
        await modlog.do_action_comment(mock_post, comment_text)

    @pytest.mark.asyncio
    async def test_do_action_remove_with_reason_valid(self):
        """Test do_action_remove_with_reason with valid reason."""
        mock_config = Mock(spec=BotConfig)
        mock_config.reddit = AsyncMock()
        mock_config.subreddit_name = "test_subreddit"
        
        modlog = ModLog(mock_config)
        
        # Mock post
        mock_post = AsyncMock()
        
        # Mock subreddit and removal reasons
        mock_subreddit = AsyncMock()
        mock_config.reddit.subreddit.return_value = mock_subreddit
        
        mock_reasons = {
            "test_reason": RemovalReasonSettings(message="Test removal message", id="reason_123")
        }
        
        with patch("rflying_tower_bot.modlog.get_current_removal_reasons", return_value=mock_reasons):
            await modlog.do_action_remove_with_reason(mock_post, "test_reason")
            
            mock_post.mod.remove.assert_called_once_with(reason_id="reason_123")
            mock_post.mod.send_removal_message.assert_called_once_with(
                "Test removal message",
                title="test_reason", 
                type="private"
            )

    @pytest.mark.asyncio
    async def test_do_action_remove_with_reason_invalid(self):
        """Test do_action_remove_with_reason with invalid reason."""
        mock_config = Mock(spec=BotConfig)
        mock_config.reddit = AsyncMock()
        mock_config.subreddit_name = "test_subreddit"
        
        modlog = ModLog(mock_config)
        
        # Mock post with proper string representation
        mock_post = AsyncMock()
        mock_post.subreddit = AsyncMock()
        mock_post.__str__ = Mock(return_value="mock_post_str")
        mock_post.__repr__ = Mock(return_value="mock_post_repr")
        
        # Mock subreddit and removal reasons (empty)
        mock_subreddit = AsyncMock()
        mock_config.reddit.subreddit.return_value = mock_subreddit
        
        mock_reasons = {}  # No valid reasons
        
        with patch("rflying_tower_bot.modlog.get_current_removal_reasons", return_value=mock_reasons):
            await modlog.do_action_remove_with_reason(mock_post, "invalid_reason")
            
            # Should send error message to subreddit
            mock_post.subreddit.message.assert_called_once()
            # Should NOT call remove or send_removal_message
            mock_post.mod.remove.assert_not_called()
            mock_post.mod.send_removal_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_do_action_remove_with_reason_none(self):
        """Test do_action_remove_with_reason with None reason."""
        mock_config = Mock(spec=BotConfig)
        modlog = ModLog(mock_config)
        
        # Mock post
        mock_post = AsyncMock()
        
        await modlog.do_action_remove_with_reason(mock_post, reason_title=None)
        
        # Should just remove without reason
        mock_post.mod.remove.assert_called_once()
        mock_post.mod.send_removal_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_do_action_remove(self):
        """Test do_action_remove method."""
        mock_config = Mock(spec=BotConfig)
        modlog = ModLog(mock_config)
        
        # Mock post
        mock_post = AsyncMock()
        
        # Mock the do_action_remove_with_reason method
        with patch.object(modlog, 'do_action_remove_with_reason') as mock_remove_with_reason:
            await modlog.do_action_remove(mock_post)
            mock_remove_with_reason.assert_called_once_with(mock_post, reason_title=None)

    @pytest.mark.asyncio
    async def test_check_post_flair_disabled(self):
        """Test check_post_flair when flair actions are disabled."""
        mock_config = Mock(spec=BotConfig)
        mock_config.rules = None
        
        modlog = ModLog(mock_config)
        mock_post = Mock()
        
        # Should return early without error
        await modlog.check_post_flair(mock_post)

    @pytest.mark.asyncio
    async def test_check_post_flair_no_rules(self):
        """Test check_post_flair when general settings disable flair actions."""
        mock_config = Mock(spec=BotConfig)
        
        # Mock rules with flair actions disabled
        mock_rules = Mock()
        mock_general_settings = Mock()
        mock_general_settings.enable_flair_actions = False
        mock_rules.general_settings = mock_general_settings
        mock_config.rules = mock_rules
        
        modlog = ModLog(mock_config)
        mock_post = Mock()
        
        # Should return early without error
        await modlog.check_post_flair(mock_post)

    @pytest.mark.asyncio
    async def test_check_post_flair_no_flair_actions(self):
        """Test check_post_flair when no flair actions are defined."""
        mock_config = Mock(spec=BotConfig)
        
        # Mock rules with flair actions enabled but no flair_actions defined
        mock_rules = Mock()
        mock_general_settings = Mock()
        mock_general_settings.enable_flair_actions = True
        mock_rules.general_settings = mock_general_settings
        mock_rules.flair_actions = None
        mock_config.rules = mock_rules
        
        modlog = ModLog(mock_config)
        mock_post = Mock()
        
        # Should return early without error
        await modlog.check_post_flair(mock_post)

    @pytest.mark.asyncio
    async def test_check_post_flair_no_matching_flair(self):
        """Test check_post_flair when post flair doesn't match any rules."""
        mock_config = Mock(spec=BotConfig)
        
        # Mock rules with flair actions enabled
        mock_rules = Mock()
        mock_general_settings = Mock()
        mock_general_settings.enable_flair_actions = True
        mock_rules.general_settings = mock_general_settings
        mock_rules.flair_actions = {"Spam": [FlairAction(action="remove")]}
        mock_config.rules = mock_rules
        
        modlog = ModLog(mock_config)
        
        # Mock post with different flair
        mock_post = Mock()
        mock_post.link_flair_text = "Different Flair"
        
        # Should return without taking any action
        await modlog.check_post_flair(mock_post)

    @pytest.mark.asyncio
    async def test_check_post_flair_with_actions(self):
        """Test check_post_flair with matching flair and actions."""
        mock_config = Mock(spec=BotConfig)
        
        # Mock rules with flair actions
        mock_rules = Mock()
        mock_general_settings = Mock()
        mock_general_settings.enable_flair_actions = True
        mock_rules.general_settings = mock_general_settings
        
        # Create flair actions
        comment_action = FlairAction(action="comment", argument="This is spam")
        remove_action = FlairAction(action="remove")
        mock_rules.flair_actions = {"Spam": [comment_action, remove_action]}
        mock_config.rules = mock_rules
        
        modlog = ModLog(mock_config)
        
        # Mock post with matching flair
        mock_post = Mock()
        mock_post.link_flair_text = "Spam"
        
        # Mock the action methods
        with patch.object(modlog, 'do_action_comment') as mock_comment:
            with patch.object(modlog, 'do_action_remove') as mock_remove:
                await modlog.check_post_flair(mock_post)
                
                # Should call both actions
                mock_comment.assert_called_once_with(mock_post, "This is spam")
                mock_remove.assert_called_once_with(mock_post)

    @pytest.mark.asyncio
    async def test_check_post_flair_invalid_action(self):
        """Test check_post_flair with invalid action."""
        mock_config = Mock(spec=BotConfig)
        
        # Mock rules with invalid flair action
        mock_rules = Mock()
        mock_general_settings = Mock()
        mock_general_settings.enable_flair_actions = True
        mock_rules.general_settings = mock_general_settings
        
        # Create invalid flair action (this would not pass validation normally)
        invalid_action = Mock()
        invalid_action.action = "invalid_action"
        invalid_action.argument = None
        mock_rules.flair_actions = {"Spam": [invalid_action]}
        mock_config.rules = mock_rules
        
        modlog = ModLog(mock_config)
        
        # Mock post with matching flair
        mock_post = Mock()
        mock_post.link_flair_text = "Spam"
        
        # Should raise NotImplementedError
        with pytest.raises(NotImplementedError, match="Invalid action invalid_action"):
            await modlog.check_post_flair(mock_post)

    @pytest.mark.asyncio
    async def test_watch_modlog_basic(self):
        """Test basic watch_modlog functionality."""
        mock_config = Mock(spec=BotConfig)
        mock_config.reddit = AsyncMock()
        mock_config.subreddit_name = "test_subreddit"
        mock_config.rules_wiki_page = "botconfig/test"
        mock_config.update_rules = AsyncMock()
        
        mock_subreddit = AsyncMock()
        mock_config.reddit.subreddit.return_value = mock_subreddit
        
        # Mock modlog entry for flair edit
        mock_flair_entry = Mock()
        mock_flair_entry.mod = "test_mod"
        mock_flair_entry.action = "editflair"
        mock_flair_entry.details = "flair edited"
        mock_flair_entry.target_permalink = "/r/test/comments/123"
        mock_flair_entry.target_fullname = "t3_123"
        
        # Mock modlog entry for wiki revision
        mock_wiki_entry = Mock()
        mock_wiki_entry.mod = "test_mod"
        mock_wiki_entry.action = "wikirevise"
        mock_wiki_entry.details = "Page botconfig/test edited"
        mock_wiki_entry.target_permalink = None
        mock_wiki_entry.target_fullname = None
        
        # Mock modlog stream - this needs to be a proper async generator
        messages_to_yield = [mock_flair_entry, mock_wiki_entry, None]
        call_count = 0
        
        async def mock_modlog_stream(**kwargs):
            nonlocal call_count
            while call_count < len(messages_to_yield):
                yield messages_to_yield[call_count]
                call_count += 1
        
        mock_subreddit.mod.stream.log = mock_modlog_stream
        
        # Mock submission for flair action
        mock_submission = AsyncMock()
        mock_config.reddit.submission.return_value = mock_submission
        
        modlog = ModLog(mock_config)
        
        with patch.object(modlog, 'check_post_flair') as mock_check_flair:
            stop_event = asyncio.Event()
            
            # Let it process some entries and then stop
            task = asyncio.create_task(modlog.watch_modlog(stop_event))
            await asyncio.sleep(0.01)  # Give it time to process
            stop_event.set()
            await task
            
            # Should check flair for the submission
            mock_check_flair.assert_called_with(mock_submission)
            # Should update rules due to wiki revision
            mock_config.update_rules.assert_called()

    @pytest.mark.asyncio
    async def test_watch_modlog_no_target_fullname(self):
        """Test watch_modlog with flair entry but no target_fullname."""
        mock_config = Mock(spec=BotConfig)
        mock_config.reddit = AsyncMock()
        mock_config.subreddit_name = "test_subreddit"
        
        mock_subreddit = AsyncMock()
        mock_config.reddit.subreddit.return_value = mock_subreddit
        
        # Mock modlog entry with no target_fullname
        mock_entry = Mock()
        mock_entry.mod = "test_mod"
        mock_entry.action = "editflair"
        mock_entry.details = "flair edited"
        mock_entry.target_permalink = "/r/test/comments/123"
        mock_entry.target_fullname = None
        
        # Mock modlog stream
        async def mock_modlog_stream(**kwargs):
            yield mock_entry
            yield None  # Causes pause_after break
        
        mock_subreddit.mod.stream.log = mock_modlog_stream
        
        modlog = ModLog(mock_config)
        
        stop_event = asyncio.Event()
        stop_event.set()  # Set immediately to exit after one iteration
        
        # Should not raise an exception
        await modlog.watch_modlog(stop_event)

    @pytest.mark.asyncio
    async def test_watch_modlog_wrong_prefix(self):
        """Test watch_modlog with target_fullname that doesn't start with t3."""
        mock_config = Mock(spec=BotConfig)
        mock_config.reddit = AsyncMock()
        mock_config.subreddit_name = "test_subreddit"
        
        mock_subreddit = AsyncMock()
        mock_config.reddit.subreddit.return_value = mock_subreddit
        
        # Mock modlog entry with t1 (comment) fullname instead of t3 (submission)
        mock_entry = Mock()
        mock_entry.mod = "test_mod"
        mock_entry.action = "editflair"
        mock_entry.details = "flair edited"
        mock_entry.target_permalink = "/r/test/comments/123/comment"
        mock_entry.target_fullname = "t1_abc"
        
        # Mock modlog stream
        async def mock_modlog_stream(**kwargs):
            yield mock_entry
            yield None  # Causes pause_after break
        
        mock_subreddit.mod.stream.log = mock_modlog_stream
        
        modlog = ModLog(mock_config)
        
        stop_event = asyncio.Event()
        stop_event.set()  # Set immediately to exit after one iteration
        
        # Should not raise an exception and should not call reddit.submission
        await modlog.watch_modlog(stop_event)
        mock_config.reddit.submission.assert_not_called()

    @pytest.mark.asyncio
    async def test_watch_modlog_request_exception(self):
        """Test watch_modlog handles RequestException."""
        mock_config = Mock(spec=BotConfig)
        mock_config.reddit = AsyncMock()
        mock_config.subreddit_name = "test_subreddit"
        
        mock_subreddit = AsyncMock()
        mock_config.reddit.subreddit.return_value = mock_subreddit
        
        # Mock modlog stream that raises RequestException
        def mock_modlog_stream(**kwargs):
            raise RequestException({}, {})
        
        mock_subreddit.mod.stream.log = mock_modlog_stream
        
        modlog = ModLog(mock_config)
        stop_event = asyncio.Event()
        
        await modlog.watch_modlog(stop_event)
        assert stop_event.is_set()

    @pytest.mark.asyncio
    async def test_watch_modlog_server_error(self):
        """Test watch_modlog handles ServerError."""
        mock_config = Mock(spec=BotConfig)
        mock_config.reddit = AsyncMock()
        mock_config.subreddit_name = "test_subreddit"
        
        mock_subreddit = AsyncMock()
        mock_config.reddit.subreddit.return_value = mock_subreddit
        
        # Mock modlog stream that raises ServerError
        def mock_modlog_stream(**kwargs):
            raise ServerError(Mock(status=500))
        
        mock_subreddit.mod.stream.log = mock_modlog_stream
        
        modlog = ModLog(mock_config)
        stop_event = asyncio.Event()
        
        await modlog.watch_modlog(stop_event)
        assert stop_event.is_set()

    @pytest.mark.asyncio
    async def test_watch_modlog_cancelled_error(self):
        """Test watch_modlog handles CancelledError."""
        mock_config = Mock(spec=BotConfig)
        mock_config.reddit = AsyncMock()
        mock_config.subreddit_name = "test_subreddit"
        
        mock_subreddit = AsyncMock()
        mock_config.reddit.subreddit.return_value = mock_subreddit
        
        # Mock modlog stream that raises CancelledError
        def mock_modlog_stream(**kwargs):
            raise asyncio.CancelledError()
        
        mock_subreddit.mod.stream.log = mock_modlog_stream
        
        modlog = ModLog(mock_config)
        stop_event = asyncio.Event()
        
        await modlog.watch_modlog(stop_event)
        assert stop_event.is_set()

    @pytest.mark.asyncio
    async def test_watch_modlog_keyboard_interrupt(self):
        """Test watch_modlog handles KeyboardInterrupt."""
        mock_config = Mock(spec=BotConfig)
        mock_config.reddit = AsyncMock()
        mock_config.subreddit_name = "test_subreddit"
        
        mock_subreddit = AsyncMock()
        mock_config.reddit.subreddit.return_value = mock_subreddit
        
        # Mock modlog stream that raises KeyboardInterrupt
        def mock_modlog_stream(**kwargs):
            raise KeyboardInterrupt()
        
        mock_subreddit.mod.stream.log = mock_modlog_stream
        
        modlog = ModLog(mock_config)
        stop_event = asyncio.Event()
        
        await modlog.watch_modlog(stop_event)
        assert stop_event.is_set()

    @pytest.mark.asyncio
    async def test_watch_modlog_general_exception(self):
        """Test watch_modlog handles general Exception."""
        mock_config = Mock(spec=BotConfig)
        mock_config.reddit = AsyncMock()
        mock_config.subreddit_name = "test_subreddit"
        
        mock_subreddit = AsyncMock()
        mock_config.reddit.subreddit.return_value = mock_subreddit
        
        # Mock modlog stream that raises general Exception
        def mock_modlog_stream(**kwargs):
            raise Exception("General error")
        
        mock_subreddit.mod.stream.log = mock_modlog_stream
        
        modlog = ModLog(mock_config)
        stop_event = asyncio.Event()
        
        await modlog.watch_modlog(stop_event)
        assert stop_event.is_set()