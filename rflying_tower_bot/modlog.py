import logging
from typing import Dict, Optional

from asyncpraw.models import Comment, Submission, Subreddit

from rflying_tower_bot.ruleset_schemas import RemovalReasonSettings

from .config import BotConfig
from .utilities import get_current_removal_reasons


class ModLog:
    """A class to react to moderator log events"""

    def __init__(self, config: BotConfig) -> None:
        """Create an instance of ModLog.

        Args:
            config (BotConfig): See config.BotConfig
        """
        self.log: logging.Logger = logging.getLogger(
            f"{__name__}.{self.__class__.__name__}"
        )
        self.config = config

    async def do_action_comment(self, post: Submission, comment: str) -> None:
        """Create a new comment that is distinguished, stickied, and approved.

        Args:
            post (Submission): The post on which to comment
            comment (str): The body of the comment
        """
        self.log.info("Commenting on %s's post: %s", post.author, post.permalink)
        c: Optional[Comment] = await post.reply(comment)
        if not c:
            self.log.error("Making comment on %s seems to have failed", str(post))
            return
        await c.mod.distinguish(sticky=True)
        await c.mod.approve()

    async def do_action_remove_with_reason(
        self, post: Submission, reason_title: Optional[str] = None
    ) -> None:
        """Remove a post and maybe send a pre-canned reason to OP.

        Args:
            post (Submission): The post to remove
            reason_title (Optional[str]): The title of the pre-canned removal reason.  If None, then no reason is used.
        """
        if reason_title:
            sub: Subreddit = await self.config.reddit.subreddit(
                self.config.subreddit_name
            )
            reasons: Dict[
                str, RemovalReasonSettings
            ] = await get_current_removal_reasons(sub)
            if reason_title not in reasons:
                self.log.error("Invalid removal reason: %sl", reason_title)
                await post.subreddit.message(
                    subject="rFlyingTower Bot Config Error",
                    message=f"While trying to remove the post {post:!}, the reason {reason_title:!} was given.\n\n"
                    f"However, no removal reason with the title {reason_title:!} could be found.",
                )
                return
            self.log.info("Removing post: %s with reason: %s", post, reason_title)
            await post.mod.remove(reason_id=reasons[reason_title].id)
            await post.mod.send_removal_message(
                reasons[reason_title].message, title=reason_title, type="private"
            )
        else:
            self.log.info("Removing post: %s", post)
            await post.mod.remove()

    async def do_action_remove(self, post: Submission) -> None:
        """Remove a post without using a pre-canned reason.

        Args:
            post (Submission): The post to remove
        """
        await self.do_action_remove_with_reason(post, reason_title=None)

    async def check_post_flair(self, post: Submission) -> None:
        """Check a post to see if it has actionable flair.

        Args:
            post (Submission): The post to check

        Raises:
            NotImplementedError: Thrown if a rule uses an unsupported action
        """
        if not self.config.rules or not self.config.rules.flair_actions:
            self.log.warning("No flair actions defined in the ruleset")
            return

        if post.link_flair_text in self.config.rules.flair_actions:
            self.log.info("Found post with flair: %s", post.link_flair_text)
            actions = self.config.rules.flair_actions[post.link_flair_text]

            for action in actions:
                try:
                    func = getattr(self, f"do_action_{action.action}")
                except AttributeError as e:
                    raise NotImplementedError(f"Invalid action {action.action}") from e
                else:
                    if action.argument:
                        await func(post, action.argument)
                    else:
                        await func(post)

    async def watch_modlog(self) -> None:
        """An infinite loop watching for modlog entries and acting on them when they match a rule."""
        subreddit: Subreddit = await self.config.reddit.subreddit(
            self.config.subreddit_name
        )
        self.log.info("Starting watch of %s's mod log", subreddit)
        async for modlog_entry in subreddit.mod.stream.log(skip_existing=True):
            self.log.debug(
                "Found new modlog entry: %s did %s (%s) to target %s",
                modlog_entry.mod,
                modlog_entry.action,
                modlog_entry.details,
                modlog_entry.target_permalink,
            )
            if (
                modlog_entry.action == "editflair"
                and modlog_entry.target_fullname
                and modlog_entry.target_fullname[:2] == "t3"
            ):
                target_name: str = modlog_entry.target_fullname[3:]
                post: Submission = await self.config.reddit.submission(id=target_name)
                await self.check_post_flair(post)

            if (
                modlog_entry.action == "wikirevise"
                and modlog_entry.details == f"Page {self.config.rules_wiki_page} edited"
            ):
                await self.config.update_rules()
