import logging
from typing import List, Optional

from asyncpraw.models.reddit.removal_reasons import RemovalReason  # type: ignore

# Utilities for dealing with removal reasons

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
