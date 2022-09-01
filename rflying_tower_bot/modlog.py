import logging
from typing import Dict, Optional

from asyncpraw.models import Comment, Submission, Subreddit  # type: ignore

from .config import BotConfig


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
        c: Comment = await post.reply(comment)
        await c.mod.distinguish(sticky=True)
        await c.mod.approve()

    async def do_action_remove_with_reason(
        self, post: Submission, reason_id: Optional[str]
    ) -> None:
        """Remove a post and maybe send a pre-canned reason to OP.

        Args:
            post (Submission): The post to remove
            reason_id (Optional[str]): The (UU?)ID of the pre-canned removal reason.  If None, then no reason is used.
        """
        if reason_id:
            sub: Subreddit = await self.config.reddit.subreddit(
                self.config.subreddit_name
            )
            reason = await sub.mod.removal_reasons.get_reason(reason_id)
            self.log.info("Removing post: %s with reason: %s", post, reason.title)
            await post.mod.remove(reason_id=reason.id)
        else:
            self.log.info("Removing post: %s", post)
            await post.mod.remove()

    async def do_action_remove(self, post: Submission) -> None:
        """Remove a post without using a pre-canned reason.

        Args:
            post (Submission): The post to remove
        """
        await self.do_action_remove_with_reason(post, reason_id=None)

    async def check_post_flair(self, post: Submission) -> None:
        """Check a post to see if it has actionable flair.

        Args:
            post (Submission): The post to check

        Raises:
            NotImplementedError: Thrown if a rule uses an unsupported action
        """
        if not self.config.rules or "flair_actions" not in self.config.rules:
            return

        flair_actions = self.config.rules["flair_actions"]
        if flair_actions and post.link_flair_text in flair_actions.keys():
            self.log.info("Found post with flair: %s", post.link_flair_text)
            actions = flair_actions[post.link_flair_text]

            for a in actions:
                if isinstance(a, Dict):
                    for action, args in a.items():
                        try:
                            func = getattr(self, f"do_action_{action}")
                        except AttributeError as e:
                            raise NotImplementedError(f"Invalid action {action}") from e
                        else:
                            await func(post, args)
                elif isinstance(a, str):
                    try:
                        func = getattr(self, f"do_action_{a}")
                    except AttributeError as e:
                        raise NotImplementedError(f"Invalid action {a}") from e
                    else:
                        await func(post)

    async def watch_modlog(self) -> None:
        """An infinite loop watching for modlog entries and acting on them when they match a rule."""
        subreddit: Subreddit = await self.config.reddit.subreddit(
            self.config.subreddit_name
        )
        self.log.info("Starting watch of %s's mod log", subreddit)
        async for modlog_entry in subreddit.mod.stream.log(skip_existing=True):
            self.log.info(
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
