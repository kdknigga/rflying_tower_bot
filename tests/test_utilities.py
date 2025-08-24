"""Tests for the utilities module."""

import pytest
from unittest.mock import Mock

from rflying_tower_bot.config import BotConfig
from rflying_tower_bot.utilities import Utilities


class TestUtilities:
    """Test the Utilities class."""

    def test_init(self):
        """Test that Utilities initializes correctly."""
        mock_config = Mock(spec=BotConfig)
        utilities = Utilities(mock_config)
        assert utilities.config == mock_config

    def test_format_comment_basic(self):
        """Test basic comment formatting."""
        mock_config = Mock(spec=BotConfig)
        mock_config.subreddit_name = "testsubreddit"
        
        utilities = Utilities(mock_config)
        body = "This is a test comment."
        
        result = utilities.format_comment(body)
        
        expected = (
            "This is a test comment."
            "\n\n --- \nI am a bot, and this action was performed automatically.  "
            "If you have any questions, please [contact the mods of this subreddit]"
            "(https://www.reddit.com/message/compose?to=/r/testsubreddit)."
        )
        
        assert result == expected

    def test_format_comment_empty_body(self):
        """Test comment formatting with empty body."""
        mock_config = Mock(spec=BotConfig)
        mock_config.subreddit_name = "emptytest"
        
        utilities = Utilities(mock_config)
        body = ""
        
        result = utilities.format_comment(body)
        
        expected = (
            ""
            "\n\n --- \nI am a bot, and this action was performed automatically.  "
            "If you have any questions, please [contact the mods of this subreddit]"
            "(https://www.reddit.com/message/compose?to=/r/emptytest)."
        )
        
        assert result == expected

    def test_format_comment_multiline_body(self):
        """Test comment formatting with multiline body."""
        mock_config = Mock(spec=BotConfig)
        mock_config.subreddit_name = "multilinetest"
        
        utilities = Utilities(mock_config)
        body = "Line 1\nLine 2\nLine 3"
        
        result = utilities.format_comment(body)
        
        expected = (
            "Line 1\nLine 2\nLine 3"
            "\n\n --- \nI am a bot, and this action was performed automatically.  "
            "If you have any questions, please [contact the mods of this subreddit]"
            "(https://www.reddit.com/message/compose?to=/r/multilinetest)."
        )
        
        assert result == expected

    def test_format_comment_special_characters(self):
        """Test comment formatting with special characters in subreddit name."""
        mock_config = Mock(spec=BotConfig)
        mock_config.subreddit_name = "test_sub-reddit"
        
        utilities = Utilities(mock_config)
        body = "Test with special chars: !@#$%^&*()"
        
        result = utilities.format_comment(body)
        
        expected = (
            "Test with special chars: !@#$%^&*()"
            "\n\n --- \nI am a bot, and this action was performed automatically.  "
            "If you have any questions, please [contact the mods of this subreddit]"
            "(https://www.reddit.com/message/compose?to=/r/test_sub-reddit)."
        )
        
        assert result == expected

    def test_format_comment_long_body(self):
        """Test comment formatting with a very long body."""
        mock_config = Mock(spec=BotConfig)
        mock_config.subreddit_name = "longtest"
        
        utilities = Utilities(mock_config)
        body = "A" * 1000  # Very long body
        
        result = utilities.format_comment(body)
        
        expected = (
            "A" * 1000
            + "\n\n --- \nI am a bot, and this action was performed automatically.  "
            "If you have any questions, please [contact the mods of this subreddit]"
            "(https://www.reddit.com/message/compose?to=/r/longtest)."
        )
        
        assert result == expected
        assert len(result) > 1000  # Ensure the format was actually applied