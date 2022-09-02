import logging
import os
from typing import Dict, List, Optional, Union, Any

from asyncpraw import Reddit
from asyncpraw.models import Subreddit
from asyncpraw.models.reddit.wikipage import WikiPage
from asyncpraw.models.reddit.removal_reasons import RemovalReason
from pydantic import BaseModel, root_validator
from pydantic_yaml import YamlModel

from . import __version__ as bot_version

log: logging.Logger = logging.getLogger(__name__)


class FlairAction(BaseModel):
    action: str
    argument: Union[str, int, None]

    @root_validator
    def valid_action(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        valid_actions = ["comment", "remove", "remove_with_reason"]
        if values["action"] not in valid_actions:
            raise ValueError(f"{values['action']} is not a valid action")

        actions_requiring_arguments = ["comment", "remove_with_reason"]
        if values["action"] in actions_requiring_arguments and (
            "argument" not in values or values["argument"] is None
        ):
            raise ValueError(f"Action {values['action']} requires an argument")

        return values


class PostFlairSettings(BaseModel):
    css_class: str = ""
    background_color: str = ""
    text_color: str = ""
    mod_only: bool = True


class Ruleset(YamlModel):
    flair_actions: Dict[str, List[FlairAction]]
    post_flair: Dict[str, PostFlairSettings]


class BotConfig:
    """General configuration for the bot, as well as a shared asyncpraw.Reddit instance."""

    def __init__(self, reddit: Reddit) -> None:
        """Init a BotConfig instance.

        Args:
            reddit (Reddit): An instance of asyncpraw.Reddit that will be used to talk to the Reddit API
        """
        self.log: logging.Logger = logging.getLogger(
            f"{__name__}.{self.__class__.__name__}"
        )
        self.reddit: Reddit = reddit
        self.subreddit_name: str = os.getenv("SUBREDDIT", "flying")
        self.rules_wiki_page = "botconfig/rflying_tower_bot"
        self.rules: Optional[Ruleset] = None

    async def update_rules(self) -> None:
        """Trigger the bot to fetch rules from the subreddit's wiki."""
        self.log.info("Updating rules from wiki")
        subreddit: Subreddit = await self.reddit.subreddit(self.subreddit_name)
        config_wiki_page: WikiPage = await subreddit.wiki.get_page(self.rules_wiki_page)
        try:
            self.rules = Ruleset.parse_raw(config_wiki_page.content_md)
        except Exception as e:
            self.log.error("Error loading rules from wiki: %s", str(e))
            await subreddit.message(
                subject="rFlyingTower Bot Config Error",
                message=f"While trying to reload the config wiki page {self.rules_wiki_page!r} an error occurred:\n\n"
                f"```\n{str(e)}\n```\n\n"
                f"The page was lasted modified by: {config_wiki_page.revision_by}",
            )
        else:
            if self.rules:
                self.log.info("Syncing post flair")
                await sync_post_flair(
                    subreddit=subreddit, post_flair_definitions=self.rules.post_flair
                )


class PRAWConfig:
    """Configuration specific to PRAW/AsyncPRAW, including Reddit app secrets and user credentials.  Most are sourced from environment variables."""

    def __init__(self) -> None:
        """Create a PRAWConfig instance.

        Raises:
            TypeError: Will be thrown if required environment variables are not set.
        """
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


def find_removal_reason(
    title: str, collection: List[RemovalReason]
) -> Optional[RemovalReason]:
    """Return a RemovalReason object based on removal reason title

    Args:
        title (str): The human-readable title of the removal reason
        collection (List[RemovalReason]): A list of removal reasons like as returned by subreddit.mod.removal_reasons

    Returns:
        Optional[RemovalReason]: Returns the RemovalReason object if found, otherwise None
    """
    return next((item for item in collection if item.title == title), None)


def find_post_flair(
    text: str, collection: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """Take a list of post flair templates and search for a specific one by "text".

    Args:
        text (str): The flair text to search for
        collection (List[Dict[str, Any]]): A list of post flair templates as provided by asyncpraw.models.Subreddit.flair.link_templates

    Returns:
        Optional[Dict[str, Any]]: A dict describing the post flair, or None if not found.
    """
    return next((item for item in collection if item["text"] == text), None)


async def sync_post_flair(
    subreddit: Subreddit, post_flair_definitions: Dict[str, PostFlairSettings]
) -> None:
    """Synchronize sub post flair with what's defined in the "post_flair" section of the rules file.  Adds or updates only, doesn't delete.

    Args:
        subreddit (Subreddit): The subreddit in which to act
        post_flair_definitions (Dict[str, PostFlairSettings]): The post flair section of the rules file
    """

    existing_flairs: List[Dict[str, Any]] = [
        flair async for flair in subreddit.flair.link_templates
    ]

    for flair in post_flair_definitions:
        if existing_flair := find_post_flair(flair, existing_flairs):
            log.info("Updaing post flair: %s", flair)
            await subreddit.flair.link_templates.update(
                template_id=existing_flair["id"],
                text=flair,
                css_class=post_flair_definitions[flair].css_class,
                background_color=post_flair_definitions[flair].background_color,
                text_color=post_flair_definitions[flair].text_color,
                mod_only=post_flair_definitions[flair].mod_only,
                fetch=True,
            )
        else:
            log.info("Adding post flair: %s", flair)
            await subreddit.flair.link_templates.add(
                text=flair,
                css_class=post_flair_definitions[flair].css_class,
                background_color=post_flair_definitions[flair].background_color,
                text_color=post_flair_definitions[flair].text_color,
                mod_only=post_flair_definitions[flair].mod_only,
            )
