"""Configuration management, including for the bot in general and rules stored in the subreddit's wiki."""

import logging
import os

import sentry_sdk
from asyncpraw import Reddit
from asyncpraw.models import Subreddit
from asyncpraw.models.reddit.removal_reasons import RemovalReason
from asyncpraw.models.reddit.wikipage import WikiPage
from dotenv import load_dotenv
from pydantic_yaml import parse_yaml_raw_as, to_yaml_str  # type: ignore

from rflying_tower_bot import __version__ as bot_version
from rflying_tower_bot.history import History
from rflying_tower_bot.ruleset_schemas import (
    PostFlairSettings,
    RemovalReasonSettings,
    Ruleset,
)

log: logging.Logger = logging.getLogger(__name__)

load_dotenv()

log_level_map: dict[str, int] = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}

log_level = os.getenv("RFTB_LOG_LEVEL", "info")
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=log_level_map.get(log_level, logging.INFO),
)

sentry_dsn = os.getenv("RFTB_SENTRY_DSN")
if sentry_dsn is not None:
    sentry_sdk.init(
        dsn=sentry_dsn,
        release=bot_version,
        environment=os.getenv("RFTB_ENVIRONMENT", "development"),
        debug=log_level == "debug",
        enable_tracing=True,
        traces_sample_rate=float(os.getenv("RFTB_SENTRY_TRACE_RATE", 0.00001)),
        profiles_sample_rate=float(os.getenv("RFTB_SENTRY_PROFILE_RATE", 0.00001)),
    )


class BotConfig:
    """General configuration for the bot, as well as a shared asyncpraw.Reddit instance."""

    def __init__(self, reddit: Reddit) -> None:
        """
        Init a BotConfig instance.

        Args:
        ----
            reddit (Reddit): An instance of asyncpraw.Reddit that will be used to talk to the Reddit API

        """
        self.log: logging.Logger = logging.getLogger(
            f"{__name__}.{self.__class__.__name__}"
        )
        self.reddit: Reddit = reddit
        self.subreddit_name: str = os.getenv("RFTB_SUBREDDIT", "flying")
        self.rules_wiki_page = "botconfig/rflying_tower_bot"
        self.rules: Ruleset | None = None
        self.history = History(
            os.getenv("RFTB_DB_CONNECTION_STRING", "sqlite+aiosqlite:///:memory:")
        )

    async def update_rules(self) -> None:
        """Trigger the bot to fetch rules from the subreddit's wiki."""
        self.log.info("Updating rules from wiki")
        subreddit: Subreddit = await self.reddit.subreddit(self.subreddit_name)
        config_wiki_page: WikiPage = await subreddit.wiki.get_page(self.rules_wiki_page)
        try:
            self.rules = parse_yaml_raw_as(Ruleset, config_wiki_page.content_md)
        except Exception as e:
            self.log.error("Error loading rules from wiki: %s", str(e))
            await subreddit.message(
                subject="rFlyingTower Bot Config Error",
                message=f"While trying to reload the config wiki page {self.rules_wiki_page!r} an error occurred:\n\n"
                f"```\n{str(e)}\n```\n\n"
                f"The page was lasted modified by: {config_wiki_page.revision_by}",
            )
        else:
            if not self.rules:
                return
            if self.rules.post_flair:
                self.log.info("Syncing post flair")
                await sync_post_flair(
                    subreddit=subreddit, pf_rules=self.rules.post_flair
                )
            if self.rules.removal_reasons:
                self.log.info("Syncing removal reasons")
                await sync_removal_reasons(
                    subreddit=subreddit, rr_rules=self.rules.removal_reasons
                )


class PRAWConfig:
    """Configuration specific to PRAW/AsyncPRAW, including Reddit app secrets and user credentials.  Most are sourced from environment variables."""

    def __init__(self) -> None:
        """
        Create a PRAWConfig instance.

        Raises
        ------
            TypeError: Will be thrown if required environment variables are not set.

        """
        self.log: logging.Logger = logging.getLogger(
            f"{__name__}.{self.__class__.__name__}"
        )

        self.client_id: str | None = os.getenv("RFTB_PRAW_CLIENT_ID")
        if self.client_id is None:
            raise TypeError("Environment variable RFTB_PRAW_CLIENT_ID is not set")

        self.client_secret: str | None = os.getenv("RFTB_PRAW_CLIENT_SECRET")
        if self.client_secret is None:
            raise TypeError("Environment variable RFTB_PRAW_CLIENT_SECRET is not set")

        self.client_user_agent: str = os.getenv(
            "RFTB_PRAW_CLIENT_USER_AGENT",
            f"Python/Linux:rFlyingTowerBot:{bot_version} (by /u/kdknigga)",
        )

        self.username: str = os.getenv("RFTB_PRAW_USERNAME", "rFlyingTower")

        self.password: str | None = os.getenv("RFTB_PRAW_PASSWORD")
        if self.client_secret is None:
            raise TypeError("Environment variable RFTB_PRAW_PASSWORD is not set")


async def get_current_post_flair(subreddit: Subreddit) -> dict[str, PostFlairSettings]:
    """
    Get the post flair currently defined in a subreddit.

    Args:
    ----
        subreddit (Subreddit): The subreddit being moderated

    Returns:
    -------
        Dict[str, PostFlairSettings]: Dict with keys being flair titles and values being PostFlairSettings

    """
    return {
        flair["text"]: PostFlairSettings.parse_obj(flair)
        async for flair in subreddit.flair.link_templates
    }


async def get_current_removal_reasons(
    subreddit: Subreddit,
) -> dict[str, RemovalReasonSettings]:
    """
    Get the removal reasons currently defined in a subreddit.

    Args:
    ----
        subreddit (Subreddit): The subreddit being moderated

    Returns:
    -------
        Dict[str, RemovalReasonSettings]: Dict with keys being removal reason titles and values being RemovalReasonSettings

    """
    return {
        reason.title: RemovalReasonSettings.parse_obj(reason.__dict__)
        async for reason in subreddit.mod.removal_reasons
    }


async def sync_removal_reasons(
    subreddit: Subreddit, rr_rules: dict[str, RemovalReasonSettings]
) -> None:
    """
    Synchronize sub removal reasons with what's defined in the "removal_reasons" section of the rules file.  Adds or updates only, doesn't delete.

    Args:
    ----
        subreddit (Subreddit): The subreddit in which to act
        rr_rules (Dict[str, RemovalReasonSettings]): The removal reasons section of the rules file

    """
    existing_reasons: dict[
        str, RemovalReasonSettings
    ] = await get_current_removal_reasons(subreddit)

    for reason in rr_rules:
        if reason in existing_reasons:
            if rr_rules[reason] != existing_reasons[reason]:
                log.info("Updating removal reason: %s", reason)
                r: RemovalReason = await subreddit.mod.removal_reasons.get_reason(
                    existing_reasons[reason].id
                )
                await r.update(message=rr_rules[reason].message)
            else:
                log.debug(
                    'Removal reason rule "%s" matches existing removal reason.  Skipping.',
                    reason,
                )
        else:
            log.info("Adding removal reason: %s", reason)
            await subreddit.mod.removal_reasons.add(
                message=rr_rules[reason].message, title=reason
            )

    return


async def sync_post_flair(
    subreddit: Subreddit, pf_rules: dict[str, PostFlairSettings]
) -> None:
    """
    Synchronize sub post flair with what's defined in the "post_flair" section of the rules file.  Adds or updates only, doesn't delete.

    Args:
    ----
        subreddit (Subreddit): The subreddit in which to act
        pf_rules (Dict[str, PostFlairSettings]): The post flair section of the rules file

    """
    existing_flairs: dict[str, PostFlairSettings] = await get_current_post_flair(
        subreddit
    )

    for flair in pf_rules:
        if flair in existing_flairs:
            if pf_rules[flair] != existing_flairs[flair]:
                log.info("Updaing post flair: %s", flair)
                await subreddit.flair.link_templates.update(
                    template_id=existing_flairs[flair].id,
                    text=flair,
                    css_class=pf_rules[flair].css_class,
                    background_color=pf_rules[flair].background_color,
                    text_color=pf_rules[flair].text_color,
                    mod_only=pf_rules[flair].mod_only,
                    fetch=True,
                )
            else:
                log.debug(
                    'Post flair rule "%s" matches existing post flair.  Skipping.',
                    flair,
                )
        else:
            log.info("Adding post flair: %s", flair)
            await subreddit.flair.link_templates.add(
                text=flair,
                css_class=pf_rules[flair].css_class,
                background_color=pf_rules[flair].background_color,
                text_color=pf_rules[flair].text_color,
                mod_only=pf_rules[flair].mod_only,
            )


async def dump_current_settings(subreddit: Subreddit, output_file: str) -> None:
    """
    Dump a subreddit's current post flair and removal reasons to a file in yaml format.

    Args:
    ----
        subreddit (Subreddit): The subreddit to read from
        output_file (str): The file to write to

    """
    ruleset = Ruleset(flair_actions=None, post_flair=None, removal_reasons=None)

    ruleset.post_flair = await get_current_post_flair(subreddit)

    ruleset.removal_reasons = await get_current_removal_reasons(subreddit)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(to_yaml_str(ruleset))
