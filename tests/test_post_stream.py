"""Tests for the post_stream module."""

import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch

from asyncpraw.exceptions import RedditAPIException
from asyncprawcore.exceptions import RequestException, ServerError

from rflying_tower_bot.config import BotConfig
from rflying_tower_bot.post_stream import PostStream


class TestPostStream:
    """Test the PostStream class."""

    def test_init(self):
        """Test PostStream initialization."""
        mock_config = Mock(spec=BotConfig)
        post_stream = PostStream(mock_config)
        
        assert post_stream.config == mock_config
        assert post_stream.utilities is not None
        assert post_stream.skip_existing is False

    @pytest.mark.asyncio
    async def test_should_process_post_disabled(self):
        """Test _should_process_post when posterity comments are disabled."""
        mock_config = Mock(spec=BotConfig)
        mock_config.rules = None
        
        post_stream = PostStream(mock_config)
        mock_post = Mock()
        
        result = await post_stream._should_process_post(mock_post)
        assert result is False

    @pytest.mark.asyncio
    async def test_should_process_post_disabled_by_setting(self):
        """Test _should_process_post when disabled by general settings."""
        mock_config = Mock(spec=BotConfig)
        
        # Mock rules with posterity comments disabled
        mock_rules = Mock()
        mock_general_settings = Mock()
        mock_general_settings.enable_create_posterity_comments = False
        mock_rules.general_settings = mock_general_settings
        mock_config.rules = mock_rules
        
        post_stream = PostStream(mock_config)
        mock_post = Mock()
        
        result = await post_stream._should_process_post(mock_post)
        assert result is False

    @pytest.mark.asyncio
    async def test_should_process_post_already_processed(self):
        """Test _should_process_post when post was already processed."""
        mock_config = Mock(spec=BotConfig)
        
        # Mock rules with posterity comments enabled
        mock_rules = Mock()
        mock_general_settings = Mock()
        mock_general_settings.enable_create_posterity_comments = True
        mock_rules.general_settings = mock_general_settings
        mock_config.rules = mock_rules
        
        # Mock history showing post was already processed
        mock_config.history = AsyncMock()
        mock_config.history.check.return_value = 1  # Already processed
        
        post_stream = PostStream(mock_config)
        mock_post = Mock()
        mock_post.permalink = "/r/test/comments/123"
        
        result = await post_stream._should_process_post(mock_post)
        assert result is False

    @pytest.mark.asyncio
    async def test_should_process_post_ignored_user(self):
        """Test _should_process_post when author is in ignore list."""
        mock_config = Mock(spec=BotConfig)
        
        # Mock rules with posterity comments enabled and ignore list
        mock_rules = Mock()
        mock_general_settings = Mock()
        mock_general_settings.enable_create_posterity_comments = True
        mock_rules.general_settings = mock_general_settings
        
        mock_posterity_settings = Mock()
        mock_posterity_settings.ignore_users = ["ignored_user", "another_ignored"]
        mock_rules.posterity_comment_settings = mock_posterity_settings
        mock_config.rules = mock_rules
        
        # Mock history showing post was not processed
        mock_config.history = AsyncMock()
        mock_config.history.check.return_value = 0
        
        post_stream = PostStream(mock_config)
        mock_post = Mock()
        mock_post.permalink = "/r/test/comments/123"
        mock_post.author = "ignored_user"
        
        result = await post_stream._should_process_post(mock_post)
        assert result is False

    @pytest.mark.asyncio
    async def test_should_process_post_valid(self):
        """Test _should_process_post when post should be processed."""
        mock_config = Mock(spec=BotConfig)
        
        # Mock rules with posterity comments enabled
        mock_rules = Mock()
        mock_general_settings = Mock()
        mock_general_settings.enable_create_posterity_comments = True
        mock_rules.general_settings = mock_general_settings
        
        mock_posterity_settings = Mock()
        mock_posterity_settings.ignore_users = ["other_user"]
        mock_rules.posterity_comment_settings = mock_posterity_settings
        mock_config.rules = mock_rules
        
        # Mock history showing post was not processed
        mock_config.history = AsyncMock()
        mock_config.history.check.return_value = 0
        
        post_stream = PostStream(mock_config)
        mock_post = Mock()
        mock_post.permalink = "/r/test/comments/123"
        mock_post.author = "valid_user"
        
        result = await post_stream._should_process_post(mock_post)
        assert result is True

    @pytest.mark.asyncio
    async def test_process_post_no_selftext(self):
        """Test _process_post when post has no selftext."""
        mock_config = Mock(spec=BotConfig)
        post_stream = PostStream(mock_config)
        
        mock_post = Mock()
        mock_post.author = "test_user"
        mock_post.permalink = "/r/test/comments/123"
        mock_post.selftext = ""
        
        # Should return without processing
        await post_stream._process_post(mock_post)

    @pytest.mark.asyncio
    async def test_process_post_with_selftext(self):
        """Test _process_post with selftext content."""
        mock_config = Mock(spec=BotConfig)
        mock_config.history = AsyncMock()
        
        # Mock utilities
        mock_utilities = Mock()
        mock_utilities.format_comment.return_value = "Formatted posterity comment"
        
        post_stream = PostStream(mock_config)
        post_stream.utilities = mock_utilities
        
        mock_post = AsyncMock()
        mock_post.author = "test_user"
        mock_post.permalink = "/r/test/comments/123"
        mock_post.selftext = "This is the original post content."
        
        # Mock comment creation
        mock_comment = AsyncMock()
        mock_post.reply.return_value = mock_comment
        
        await post_stream._process_post(mock_post)
        
        # Should create comment and mark as processed
        mock_post.reply.assert_called_once()
        mock_comment.mod.distinguish.assert_called_once_with(sticky=False)
        mock_comment.mod.lock.assert_called_once()
        mock_config.history.add.assert_called_once_with("/r/test/comments/123", "save_post_body")

    @pytest.mark.asyncio
    async def test_process_post_long_content(self):
        """Test _process_post with content longer than 9500 characters."""
        mock_config = Mock(spec=BotConfig)
        mock_config.history = AsyncMock()
        
        # Mock utilities
        mock_utilities = Mock()
        mock_utilities.format_comment.return_value = "Formatted posterity comment"
        
        post_stream = PostStream(mock_config)
        post_stream.utilities = mock_utilities
        
        mock_post = AsyncMock()
        mock_post.author = "test_user"
        mock_post.permalink = "/r/test/comments/123"
        mock_post.selftext = "A" * 10000  # Long content
        
        # Mock comment creation
        mock_comment = AsyncMock()
        mock_post.reply.return_value = mock_comment
        
        await post_stream._process_post(mock_post)
        
        # Should create comment with truncated content
        mock_post.reply.assert_called_once()
        call_args = mock_post.reply.call_args[0][0]
        # Should contain truncated content and ellipsis
        assert "..." in call_args
        
        mock_config.history.add.assert_called_once_with("/r/test/comments/123", "save_post_body")

    @pytest.mark.asyncio
    async def test_process_post_comment_fails(self):
        """Test _process_post when comment creation fails."""
        mock_config = Mock(spec=BotConfig)
        mock_config.history = AsyncMock()
        
        # Mock utilities
        mock_utilities = Mock()
        mock_utilities.format_comment.return_value = "Formatted posterity comment"
        
        post_stream = PostStream(mock_config)
        post_stream.utilities = mock_utilities
        
        mock_post = AsyncMock()
        mock_post.author = "test_user"
        mock_post.permalink = "/r/test/comments/123"
        mock_post.selftext = "This is the original post content."
        
        # Mock comment creation failure
        mock_post.reply.return_value = None
        
        await post_stream._process_post(mock_post)
        
        # Should not call history.add or comment methods
        mock_config.history.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_post_reddit_api_exception(self):
        """Test _process_post when Reddit API raises exception."""
        mock_config = Mock(spec=BotConfig)
        mock_config.history = AsyncMock()
        
        # Mock utilities
        mock_utilities = Mock()
        mock_utilities.format_comment.return_value = "Formatted posterity comment"
        
        post_stream = PostStream(mock_config)
        post_stream.utilities = mock_utilities
        
        mock_post = AsyncMock()
        mock_post.author = "test_user"
        mock_post.permalink = "/r/test/comments/123"
        mock_post.selftext = "This is the original post content."
        
        # Mock Reddit API exception
        mock_error = Mock()
        mock_error.error_type = "RATELIMIT"
        mock_exception = RedditAPIException([mock_error])
        mock_post.reply.side_effect = mock_exception
        
        # Should not raise exception and should handle gracefully
        await post_stream._process_post(mock_post)

    @pytest.mark.asyncio
    async def test_process_post_reddit_api_exception_other(self):
        """Test _process_post with non-ratelimit Reddit API exception."""
        mock_config = Mock(spec=BotConfig)
        mock_config.history = AsyncMock()
        
        # Mock utilities
        mock_utilities = Mock()
        mock_utilities.format_comment.return_value = "Formatted posterity comment"
        
        post_stream = PostStream(mock_config)
        post_stream.utilities = mock_utilities
        
        mock_post = AsyncMock()
        mock_post.author = "test_user"
        mock_post.permalink = "/r/test/comments/123"
        mock_post.selftext = "This is the original post content."
        
        # Mock Reddit API exception (non-ratelimit)
        mock_error = Mock()
        mock_error.error_type = "OTHER_ERROR"
        mock_exception = RedditAPIException([mock_error])
        mock_post.reply.side_effect = mock_exception
        
        await post_stream._process_post(mock_post)
        
        # Should mark as processed even on error
        mock_config.history.add.assert_called_once_with("/r/test/comments/123", "save_post_body")

    @pytest.mark.asyncio
    async def test_watch_poststream_basic(self):
        """Test basic watch_poststream functionality."""
        mock_config = Mock(spec=BotConfig)
        mock_config.reddit = AsyncMock()
        mock_config.subreddit_name = "test_subreddit"
        
        mock_subreddit = AsyncMock()
        mock_config.reddit.subreddit.return_value = mock_subreddit
        
        post_stream = PostStream(mock_config)
        
        # Mock _watch_submissions to avoid complexity
        with patch.object(post_stream, '_watch_submissions') as mock_watch:
            stop_event = asyncio.Event()
            stop_event.set()  # Set immediately to exit
            
            await post_stream.watch_poststream(stop_event)
            mock_watch.assert_called_once_with(mock_subreddit)

    @pytest.mark.asyncio
    async def test_watch_poststream_request_exception(self):
        """Test watch_poststream handles RequestException."""
        mock_config = Mock(spec=BotConfig)
        mock_config.reddit = AsyncMock()
        mock_config.subreddit_name = "test_subreddit"
        
        mock_subreddit = AsyncMock()
        mock_config.reddit.subreddit.return_value = mock_subreddit
        
        post_stream = PostStream(mock_config)
        
        # Mock _watch_submissions to raise RequestException
        with patch.object(post_stream, '_watch_submissions') as mock_watch:
            mock_watch.side_effect = RequestException({}, {})
            
            stop_event = asyncio.Event()
            
            await post_stream.watch_poststream(stop_event)
            assert stop_event.is_set()

    @pytest.mark.asyncio
    async def test_watch_poststream_server_error(self):
        """Test watch_poststream handles ServerError."""
        mock_config = Mock(spec=BotConfig)
        mock_config.reddit = AsyncMock()
        mock_config.subreddit_name = "test_subreddit"
        
        mock_subreddit = AsyncMock()
        mock_config.reddit.subreddit.return_value = mock_subreddit
        
        post_stream = PostStream(mock_config)
        
        # Mock _watch_submissions to raise ServerError
        with patch.object(post_stream, '_watch_submissions') as mock_watch:
            mock_watch.side_effect = ServerError(Mock(status=500))
            
            stop_event = asyncio.Event()
            
            await post_stream.watch_poststream(stop_event)
            assert stop_event.is_set()

    @pytest.mark.asyncio
    async def test_watch_poststream_cancelled_error(self):
        """Test watch_poststream handles CancelledError."""
        mock_config = Mock(spec=BotConfig)
        mock_config.reddit = AsyncMock()
        mock_config.subreddit_name = "test_subreddit"
        
        mock_subreddit = AsyncMock()
        mock_config.reddit.subreddit.return_value = mock_subreddit
        
        post_stream = PostStream(mock_config)
        
        # Mock _watch_submissions to raise CancelledError
        with patch.object(post_stream, '_watch_submissions') as mock_watch:
            mock_watch.side_effect = asyncio.CancelledError()
            
            stop_event = asyncio.Event()
            
            await post_stream.watch_poststream(stop_event)
            assert stop_event.is_set()

    @pytest.mark.asyncio
    async def test_watch_poststream_keyboard_interrupt(self):
        """Test watch_poststream handles KeyboardInterrupt."""
        mock_config = Mock(spec=BotConfig)
        mock_config.reddit = AsyncMock()
        mock_config.subreddit_name = "test_subreddit"
        
        mock_subreddit = AsyncMock()
        mock_config.reddit.subreddit.return_value = mock_subreddit
        
        post_stream = PostStream(mock_config)
        
        # Mock _watch_submissions to raise KeyboardInterrupt
        with patch.object(post_stream, '_watch_submissions') as mock_watch:
            mock_watch.side_effect = KeyboardInterrupt()
            
            stop_event = asyncio.Event()
            
            await post_stream.watch_poststream(stop_event)
            assert stop_event.is_set()

    @pytest.mark.asyncio
    async def test_watch_poststream_general_exception(self):
        """Test watch_poststream handles general Exception."""
        mock_config = Mock(spec=BotConfig)
        mock_config.reddit = AsyncMock()
        mock_config.subreddit_name = "test_subreddit"
        
        mock_subreddit = AsyncMock()
        mock_config.reddit.subreddit.return_value = mock_subreddit
        
        post_stream = PostStream(mock_config)
        
        # Mock _watch_submissions to raise general Exception
        with patch.object(post_stream, '_watch_submissions') as mock_watch:
            mock_watch.side_effect = Exception("General error")
            
            stop_event = asyncio.Event()
            
            await post_stream.watch_poststream(stop_event)
            assert stop_event.is_set()

    @pytest.mark.asyncio
    async def test_watch_submissions_basic(self):
        """Test _watch_submissions basic functionality."""
        mock_config = Mock(spec=BotConfig)
        post_stream = PostStream(mock_config)
        
        # Mock subreddit with stream
        mock_subreddit = AsyncMock()
        mock_post1 = Mock()
        mock_post2 = Mock()
        
        # Mock submission stream
        async def mock_submission_stream(**kwargs):
            yield mock_post1
            yield mock_post2
            yield None  # Causes pause_after break
            
        mock_subreddit.stream.submissions = mock_submission_stream
        
        # Mock the should_process and process methods
        with patch.object(post_stream, '_should_process_post') as mock_should:
            with patch.object(post_stream, '_process_post') as mock_process:
                mock_should.side_effect = [True, False]  # Process first, skip second
                
                await post_stream._watch_submissions(mock_subreddit)
                
                # Should check both posts
                assert mock_should.call_count == 2
                # Should only process the first post
                mock_process.assert_called_once_with(mock_post1)
                
                # skip_existing should be set to True after None
                assert post_stream.skip_existing is True