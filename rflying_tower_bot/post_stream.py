"""A module to react to new posts."""

import logging
import time

from asyncpraw.models import Comment, Subreddit
from asyncprawcore.exceptions import RequestException, ServerError

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
        while True:
            try:
                async for post in subreddit.stream.submissions():
                    if (
                        not self.config.rules
                        or not self.config.rules.general_settings.enable_create_posterity_comments
                    ):
                        self.log.debug("Posterity comments disabled, skipping post")
                        continue

                    if (
                        await self.config.history.check(
                            post.permalink, "save_post_body"
                        )
                        > 0
                    ):
                        self.log.info(
                            "Skipping post %s, already processed", post.permalink
                        )
                        continue

                    if (
                        post.author
                        in self.config.rules.posterity_comment_settings.ignore_users
                    ):
                        self.log.info(
                            "Skipping post %s, author %s is in ignore list",
                            post.permalink,
                            post.author,
                        )
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
                            "Comment created with post body for posterity: %s",
                            c.permalink,
                        )

            except (RequestException, ServerError) as e:
                self.log.warning("Server error in post stream watcher: %s", e)
                # Yes, I know a blocking sleep in async code is bad, but if Reddit is having a problem might as well pause the whole bot
                time.sleep(60)
            except KeyboardInterrupt:
                self.log.info("Caught keyboard interrupt, exiting post stream watcher")
                break
            except Exception as e:
                self.log.error("Error in post stream watcher: %s", e)
