import logging
import os
from typing import Dict, Optional

import yaml
from asyncpraw import Reddit # type: ignore
from asyncpraw.models import Subreddit # type: ignore
from asyncpraw.models.reddit.wikipage import WikiPage # type: ignore

from . import __version__ as bot_version


class BotConfig:
    def __init__(self, reddit: Reddit) -> None:
        self.log: logging.Logger = logging.getLogger(
            f"{__name__}.{self.__class__.__name__}"
        )
        self.reddit: Reddit = reddit
        self.subreddit_name: str = os.getenv("SUBREDDIT", "flying")
        self.rules_wiki_page = "botconfig/rflying_tower_bot"
        self.rules: Optional[Dict] = None

    async def update_rules(self) -> None:
        self.log.info("Updating rules from wiki")
        subreddit: Subreddit = await self.reddit.subreddit(self.subreddit_name)
        config_wiki_page: WikiPage = await subreddit.wiki.get_page(self.rules_wiki_page)
        try:
            self.rules = yaml.safe_load(config_wiki_page.content_md)
        except yaml.scanner.ScannerError as e:
            self.log.error("Error loading rules from wiki: %s", str(e))
            await subreddit.message(
                subject="rFlyingTower Bot Config Error",
                message=f"While trying to reload the config wiki page {self.rules_wiki_page!r} an error occurred:\n\n"
                f"```\n{str(e)}\n```\n\n"
                f"The page was lasted modified by: {config_wiki_page.revision_by}",
            )


class PRAWConfig:
    def __init__(self) -> None:
        self.log: logging.Logger = logging.getLogger(
            f"{__name__}.{self.__class__.__name__}"
        )

        self.client_id: Optional[str] = os.getenv("PRAW_CLIENT_ID")
        if self.client_id is None:
            raise TypeError("Environment variable PRAW_CLIENT_ID is not set")

        self.client_secret: Optional[str] = os.getenv("PRAW_CLIENT_SECRET")
        if self.client_secret is None:
            raise TypeError("Environment variable PRAW_CLIENT_SECRET is not set")

        self.client_user_agent: str = os.getenv(
            "PRAW_CLIENT_USER_AGENT",
            f"Python/Linux:rFlyingTowerBot:{bot_version} (by /u/kdknigga)",
        )

        self.username: str = os.getenv("PRAW_USERNAME", "rFlyingTower")

        self.password: Optional[str] = os.getenv("PRAW_PASSWORD")
        if self.client_secret is None:
            raise TypeError("Environment variable PRAW_PASSWORD is not set")
