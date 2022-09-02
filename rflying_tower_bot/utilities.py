import logging
from typing import Any, Dict, List, Optional

from asyncpraw.models import Subreddit
from asyncpraw.models.reddit.removal_reasons import RemovalReason

from .ruleset_schemas import PostFlairSettings

log: logging.Logger = logging.getLogger(__name__)


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
