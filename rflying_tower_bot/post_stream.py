"""A module to react to new posts."""

import logging

from asyncpraw.models import Comment, Subreddit

from rflying_tower_bot.config import BotConfig
from rflying_tower_bot.utilities import Utilities


class PostStream:
    """A class to react to new posts."""

    def __init__(self, config: BotConfig) -> None:
        """
        Create an instance of PostStream.

        Args:
        ----
            config (BotConfig): See config.BotConfig

        """
        self.log: logging.Logger = logging.getLogger(
            f"{__name__}.{self.__class__.__name__}"
        )
        self.config = config
        self.utilities = Utilities(config)

    async def watch_poststream(self) -> None:
        """Watch the post stream and react to new posts."""
        subreddit: Subreddit = await self.config.reddit.subreddit(
            self.config.subreddit_name
        )
        self.log.info("Watching the post stream for new posts in %s", subreddit)
        async for post in subreddit.stream.submissions():
            if await self.config.history.check(post.permalink, "save_post_body") > 0:
                self.log.info("Skipping post %s, already processed", post.permalink)
                continue

            self.log.info("New post from %s: %s", post.author, post.permalink)
            if post.selftext != "":
                comment_text = f"This is a copy of the original post body for posterity:\n\n --- \n{post.selftext}"
                c: Comment | None = await post.reply(
                    self.utilities.format_comment(comment_text)
                )
                if not c:
                    self.log.error(
                        "Making comment on %s seems to have failed", str(post)
                    )
                    return
                await c.mod.distinguish(sticky=False)
                await self.config.history.add(post.permalink, "save_post_body")
                self.log.info(
                    "Comment created with post body for posterity: %s", c.permalink
                )
