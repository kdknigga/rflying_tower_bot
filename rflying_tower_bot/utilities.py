"""Provides utility functions for the rflying_tower_bot."""

import logging

from rflying_tower_bot.config import BotConfig

log: logging.Logger = logging.getLogger(__name__)


class Utilities:
    """Utility functions."""

    def __init__(self, config: BotConfig) -> None:
        """
        Initialize the Utilities class.

        Args:
        ----
            config (BotConfig): The configuration object for the bot.

        Returns:
        -------
            None

        """
        self.config = config

    def format_comment(self, body: str) -> str:
        """
        Add the standard 'I'm a bot' disclaimer to some string to be used as a comment.

        Args:
        ----
            body (str): Something to submit as a comment

        Returns:
        -------
            str: Your comment, plus boilerplate

        """
        return (
            body
            + "\n\n --- \nI am a bot, and this action was performed automatically.  "
            f"If you have any questions, please [contact the mods of this subreddit](https://www.reddit.com/message/compose?to=/r/{self.config.subreddit_name})."  # noqa: E501
        )
