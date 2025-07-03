"""Tests for the ruleset_schemas module."""

import pytest
from pydantic import ValidationError

from rflying_tower_bot.ruleset_schemas import (
    FlairAction,
    GeneralSettings,
    PostFlairSettings,
    PosterityCommentSettings,
    RemovalReasonSettings,
    Ruleset,
)


class TestGeneralSettings:
    """Test the GeneralSettings class."""

    def test_default_values(self):
        """Test that GeneralSettings has correct default values."""
        settings = GeneralSettings()
        assert settings.enable_sync_removal_reasons is True
        assert settings.enable_sync_post_flair is True
        assert settings.enable_flair_actions is True
        assert settings.enable_create_posterity_comments is True
        assert settings.enable_inbox_actions is True

    def test_custom_values(self):
        """Test that GeneralSettings accepts custom values."""
        settings = GeneralSettings(
            enable_sync_removal_reasons=False,
            enable_sync_post_flair=False,
            enable_flair_actions=False,
            enable_create_posterity_comments=False,
            enable_inbox_actions=False,
        )
        assert settings.enable_sync_removal_reasons is False
        assert settings.enable_sync_post_flair is False
        assert settings.enable_flair_actions is False
        assert settings.enable_create_posterity_comments is False
        assert settings.enable_inbox_actions is False


class TestPosterityCommentSettings:
    """Test the PosterityCommentSettings class."""

    def test_default_values(self):
        """Test that PosterityCommentSettings has correct default values."""
        settings = PosterityCommentSettings()
        assert settings.ignore_users == []

    def test_custom_values(self):
        """Test that PosterityCommentSettings accepts custom values."""
        ignore_list = ["user1", "user2", "user3"]
        settings = PosterityCommentSettings(ignore_users=ignore_list)
        assert settings.ignore_users == ignore_list


class TestFlairAction:
    """Test the FlairAction class."""

    def test_valid_comment_action(self):
        """Test valid comment action with argument."""
        action = FlairAction(action="comment", argument="Test comment")
        assert action.action == "comment"
        assert action.argument == "Test comment"

    def test_valid_remove_action(self):
        """Test valid remove action without argument."""
        action = FlairAction(action="remove")
        assert action.action == "remove"
        assert action.argument is None

    def test_valid_remove_with_reason_action(self):
        """Test valid remove_with_reason action with argument."""
        action = FlairAction(action="remove_with_reason", argument="rule_violation")
        assert action.action == "remove_with_reason"
        assert action.argument == "rule_violation"

    def test_invalid_action(self):
        """Test that invalid action raises ValidationError."""
        with pytest.raises(ValidationError, match="invalid_action is not a valid action"):
            FlairAction(action="invalid_action")

    def test_comment_action_missing_argument(self):
        """Test that comment action without argument raises ValidationError."""
        with pytest.raises(ValidationError, match="Action comment requires an argument"):
            FlairAction(action="comment")

    def test_remove_with_reason_action_missing_argument(self):
        """Test that remove_with_reason action without argument raises ValidationError."""
        with pytest.raises(ValidationError, match="Action remove_with_reason requires an argument"):
            FlairAction(action="remove_with_reason")

    def test_action_with_int_argument(self):
        """Test that action accepts integer argument."""
        action = FlairAction(action="comment", argument=42)
        assert action.action == "comment"
        assert action.argument == 42


class TestPostFlairSettings:
    """Test the PostFlairSettings class."""

    def test_default_values(self):
        """Test that PostFlairSettings has correct default values."""
        settings = PostFlairSettings()
        assert settings.css_class == ""
        assert settings.background_color == "#dadada"
        assert settings.text_color == "dark"
        assert settings.mod_only is True
        assert settings.id is None

    def test_custom_values(self):
        """Test that PostFlairSettings accepts custom values."""
        settings = PostFlairSettings(
            css_class="custom-class",
            background_color="#ff0000",
            text_color="light",
            mod_only=False,
            id="flair_123",
        )
        assert settings.css_class == "custom-class"
        assert settings.background_color == "#ff0000"
        assert settings.text_color == "light"
        assert settings.mod_only is False
        # id field is excluded from serialization but still accessible
        assert settings.id == "flair_123"


class TestRemovalReasonSettings:
    """Test the RemovalReasonSettings class."""

    def test_creation_with_message(self):
        """Test that RemovalReasonSettings requires a message."""
        message = "Your post has been removed for violating rule 1."
        settings = RemovalReasonSettings(message=message)
        assert settings.message == message
        assert settings.id is None

    def test_creation_with_message_and_id(self):
        """Test that RemovalReasonSettings accepts message and id."""
        message = "Your post has been removed."
        reason_id = "reason_123"
        settings = RemovalReasonSettings(message=message, id=reason_id)
        assert settings.message == message
        # id field is excluded from serialization but still accessible
        assert settings.id == reason_id

    def test_missing_message_raises_error(self):
        """Test that RemovalReasonSettings without message raises ValidationError."""
        with pytest.raises(ValidationError):
            RemovalReasonSettings()


class TestRuleset:
    """Test the Ruleset class."""

    def test_default_values(self):
        """Test that Ruleset has correct default values."""
        ruleset = Ruleset()
        assert isinstance(ruleset.general_settings, GeneralSettings)
        assert isinstance(ruleset.posterity_comment_settings, PosterityCommentSettings)
        assert ruleset.flair_actions is None
        assert ruleset.post_flair is None
        assert ruleset.removal_reasons is None

    def test_with_custom_settings(self):
        """Test that Ruleset accepts custom settings."""
        general_settings = GeneralSettings(enable_flair_actions=False)
        posterity_settings = PosterityCommentSettings(ignore_users=["test_user"])
        
        ruleset = Ruleset(
            general_settings=general_settings,
            posterity_comment_settings=posterity_settings,
        )
        
        assert ruleset.general_settings.enable_flair_actions is False
        assert ruleset.posterity_comment_settings.ignore_users == ["test_user"]

    def test_with_flair_actions(self):
        """Test that Ruleset accepts flair actions."""
        flair_actions = {
            "Rule Violation": [
                FlairAction(action="comment", argument="Please follow the rules"),
                FlairAction(action="remove"),
            ]
        }
        
        ruleset = Ruleset(flair_actions=flair_actions)
        assert ruleset.flair_actions == flair_actions

    def test_with_post_flair(self):
        """Test that Ruleset accepts post flair settings."""
        post_flair = {
            "Question": PostFlairSettings(css_class="question", background_color="#blue"),
            "Discussion": PostFlairSettings(css_class="discussion"),
        }
        
        ruleset = Ruleset(post_flair=post_flair)
        assert ruleset.post_flair == post_flair

    def test_with_removal_reasons(self):
        """Test that Ruleset accepts removal reasons."""
        removal_reasons = {
            "Spam": RemovalReasonSettings(message="This post has been removed as spam."),
            "Rule 1": RemovalReasonSettings(message="Please follow rule 1."),
        }
        
        ruleset = Ruleset(removal_reasons=removal_reasons)
        assert ruleset.removal_reasons == removal_reasons

    def test_full_ruleset(self):
        """Test a complete ruleset with all components."""
        general_settings = GeneralSettings(enable_sync_removal_reasons=False)
        posterity_settings = PosterityCommentSettings(ignore_users=["mod1", "mod2"])
        flair_actions = {
            "Approved": [FlairAction(action="comment", argument="This post is approved")]
        }
        post_flair = {
            "Meta": PostFlairSettings(css_class="meta", mod_only=False)
        }
        removal_reasons = {
            "Off-topic": RemovalReasonSettings(message="This post is off-topic.")
        }
        
        ruleset = Ruleset(
            general_settings=general_settings,
            posterity_comment_settings=posterity_settings,
            flair_actions=flair_actions,
            post_flair=post_flair,
            removal_reasons=removal_reasons,
        )
        
        assert ruleset.general_settings.enable_sync_removal_reasons is False
        assert ruleset.posterity_comment_settings.ignore_users == ["mod1", "mod2"]
        assert ruleset.flair_actions == flair_actions
        assert ruleset.post_flair == post_flair
        assert ruleset.removal_reasons == removal_reasons