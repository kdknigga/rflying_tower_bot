"""A module to react to new posts."""

import asyncio
import logging

from asyncpraw.exceptions import RedditAPIException
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
        self.skip_existing = False

    async def watch_poststream(self, stop_event: asyncio.Event) -> None:
        """Watch the post stream and react to new posts."""
        subreddit: Subreddit = await self.config.reddit.subreddit(
            self.config.subreddit_name
        )
        self.log.info("Watching the post stream for new posts in %s", subreddit)
        while not stop_event.is_set():
            try:
                await self._watch_submissions(subreddit)
            except (RequestException, ServerError) as e:
                self.log.error("Server error in post stream watcher: %s.  Exiting.", e)
                break
            except asyncio.CancelledError:
                self.log.info("Post stream watcher cancelled, exiting")
                stop_event.set()
                break
            except KeyboardInterrupt:
                self.log.info("Caught keyboard interrupt, exiting post stream watcher")
                stop_event.set()
                break
            except Exception as e:
                self.log.error(
                    "Error in post stream watcher: %s.  Exiting.", e, exc_info=True
                )
                stop_event.set()
                break

    async def _watch_submissions(self, subreddit: Subreddit) -> None:
        """Watch submissions in the subreddit."""
        async for post in subreddit.stream.submissions(
            skip_existing=self.skip_existing, pause_after=6
        ):
            # Break out of the for loop occasionally if there's nothing going on for a while
            # to check if the stop_event is set.  post will be None if pause_after is reached
            if post is None:
                self.log.debug("Pausing post stream")
                self.skip_existing = True
                break

            if not await self._should_process_post(post):
                continue
            await self._process_post(post)

    async def _should_process_post(self, post) -> bool:
        """Determine if a post should be processed."""
        if (
            not self.config.rules
            or not self.config.rules.general_settings.enable_create_posterity_comments
        ):
            self.log.debug("Posterity comments disabled, skipping post")
            return False

        if await self.config.history.check(post.permalink, "save_post_body") > 0:
            self.log.info("Skipping post %s, already processed", post.permalink)
            return False

        if post.author in self.config.rules.posterity_comment_settings.ignore_users:
            self.log.info(
                "Skipping post %s, author %s is in ignore list",
                post.permalink,
                post.author,
            )
            return False

        return True

    async def _process_post(self, post) -> None:
        """Process a new post."""
        self.log.info("New post from %s: %s", post.author, post.permalink)
        if post.selftext != "":
            # Reddit comments have a max length of 10,000 characters, so truncate the post body if it's too long
            # Leave room for the bot header and footer
            truncated_original_post_body: str = post.selftext[:9500] + (
                post.selftext[9500:] and "..."
            )
            comment_text = f"This is a copy of the original post body for posterity:\n\n --- \n{truncated_original_post_body} \n\n --- \n Please downvote this comment until it collapses.\n\n"
            c: Comment | None = None
            try:
                c = await post.reply(self.utilities.format_comment(comment_text))
            except RedditAPIException as e:
                for sube in e.items:
                    self.log.error(
                        "API error making comment on %s: %s.",
                        post.permalink,
                        sube,
                    )

                    match sube.error_type:
                        case "RATELIMIT":
                            self.log.warning("Rate limit hit, sleeping for 15 minutes")
                            await asyncio.sleep(900)

                        # case "TOO_LONG":
                        case _:
                            self.log.error("Marking post as processed and moving on.")

                            await self.config.history.add(
                                post.permalink, "save_post_body"
                            )

            if not c:
                self.log.error("Making comment on %s seems to have failed", str(post))
                return
            await c.mod.distinguish(sticky=False)
            await c.mod.lock()
            await self.config.history.add(post.permalink, "save_post_body")
            self.log.info(
                "Comment created with post body for posterity: %s",
                c.permalink,
            )
