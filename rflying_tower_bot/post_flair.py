import logging

from typing import Dict, List, Optional

from asyncpraw.models import Subreddit  # type: ignore

# Utilities for dealing with post flair templates


def find_post_flair(text: str, collection: List[Dict]) -> Optional[Dict]:
    """Take a list of post flair templates and search for a specific one by "text".

    Args:
        text (str): The flair text to search for
        collection (List[Dict]): A list of post flair templates as provided by asyncpraw.models.Subreddit.flair.link_templates

    Returns:
        Optional[Dict]: A dict describing the post flair, or None if not found.
    """
    return next((item for item in collection if item["text"] == text), None)


async def sync_post_flair(
    subreddit: Subreddit, post_flair_definitions: Dict[str, Dict]
) -> None:
    """Synchronize sub post flair with what's defined in the "post_flair" section of the rules file.  Adds or updates only, doesn't delete.

    Args:
        subreddit (Subreddit): The subreddit in which to act
        post_flair_definitions (Dict[str, Dict]): The post flair section of the rules file
    """
    existing_flairs: List[Dict] = [
        flair async for flair in subreddit.flair.link_templates
    ]
    for flair in post_flair_definitions:
        if existing_flair := find_post_flair(flair, existing_flairs):
            logging.info("Updaing post flair: %s", flair)
            await subreddit.flair.link_templates.update(
                template_id=existing_flair["id"],
                text=flair,
                css_class=post_flair_definitions[flair]["css_class"],
                background_color=post_flair_definitions[flair]["background_color"],
                text_color=post_flair_definitions[flair]["text_color"],
                mod_only=post_flair_definitions[flair]["mod_only"],
                fetch=True,
            )
        else:
            logging.info("Adding post flair: %s", flair)
            await subreddit.flair.link_templates.add(
                text=flair,
                css_class=post_flair_definitions[flair]["css_class"],
                background_color=post_flair_definitions[flair]["background_color"],
                text_color=post_flair_definitions[flair]["text_color"],
                mod_only=post_flair_definitions[flair]["mod_only"],
            )
