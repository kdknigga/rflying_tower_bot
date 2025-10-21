"""A module to react to moderator log events."""

import asyncio
import logging

from asyncpraw.models import Comment, Redditor, Submission, Subreddit
from asyncprawcore.exceptions import RequestException, ServerError

from rflying_tower_bot.config import BotConfig, get_current_removal_reasons
from rflying_tower_bot.ruleset_schemas import RemovalReasonSettings
from rflying_tower_bot.utilities import Utilities


class ModLog:
    """A class to react to moderator log events."""

    def __init__(self, config: BotConfig) -> None:
        """
        Create an instance of ModLog.

        Args:
        ----
            config (BotConfig): See config.BotConfig

        """
        self.log: logging.Logger = logging.getLogger(
            f"{__name__}.{self.__class__.__name__}"
        )
        self.config = config
        self.utilities = Utilities(config)

    async def do_action_comment(self, post: Submission, comment: str) -> None:
        """
        Create a new comment that is distinguished, stickied, and approved.

        Args:
        ----
            post (Submission): The post on which to comment
            comment (str): The body of the comment

        """
        self.log.info("Commenting on %s's post: %s", post.author, post.permalink)
        c = await post.reply(self.utilities.format_comment(comment))
        if not c:
            self.log.error("Making comment on %s seems to have failed", str(post))
            return
        await c.mod.distinguish(sticky=True)
        await c.mod.approve()

    async def do_action_remove_with_reason(
        self, post: Comment | Submission, reason_title: str | None = None
    ) -> None:
        """
        Remove a post and maybe send a pre-canned reason to OP.

        Args:
        ----
            post (Comment | Submission): The post to remove
            reason_title (Optional[str]): The title of the pre-canned removal reason.  If None, then no reason is used.

        """
        if reason_title:
            sub: Subreddit = await self.config.reddit.subreddit(
                self.config.subreddit_name
            )
            reasons: dict[
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

    async def do_action_remove(self, post: Comment | Submission) -> None:
        """
        Remove a post without using a pre-canned reason.

        Args:
        ----
            post (Comment | Submission): The post to remove

        """
        await self.do_action_remove_with_reason(post, reason_title=None)

    async def do_action_ban(
        self, user: Redditor, reason: str, message: str = ""
    ) -> None:
        """
        Ban a user with a given reason.

        Args:
        ----
            user (Redditor): The user to ban
            reason (str): The reason for the ban for the modlog
            message (str): The message to send to the user, if any

        """
        subreddit: Subreddit = await self.config.reddit.subreddit(
            self.config.subreddit_name
        )
        self.log.info("Banning user %s with reason: %s", user.name, reason)
        await subreddit.banned.add(user.name, ban_reason=reason, ban_message=message)

    async def handle_ban_evasion(
        self, post: Comment | Submission, user: Redditor
    ) -> None:
        """
        Handle ban evasion by removing the post/comment and banning the user.

        Args:
        ----
            post (Submission | Comment): The post or comment to remove
            user (Redditor): The user to ban

        """
        self.log.warning(
            "Detected ban evasion by %s on %s, removing and banning",
            user.name,
            post.permalink,
        )
        await self.do_action_remove(post)
        await self.do_action_ban(user, "Ban evasion", "Ban evasion")

    async def check_post_flair(self, post: Submission) -> None:
        """
        Check a post to see if it has actionable flair.

        Args:
        ----
            post (Submission): The post to check

        Raises:
        ------
            NotImplementedError: Thrown if a rule uses an unsupported action

        """
        if (
            not self.config.rules
            or not self.config.rules.general_settings.enable_flair_actions
        ):
            self.log.debug("Flair actions are disabled")
            return

        if not self.config.rules.flair_actions:
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

    async def watch_modlog(self, stop_event: asyncio.Event) -> None:
        """Watch for modlog entries and act on them when they match a rule, in an infinite loop."""
        subreddit: Subreddit = await self.config.reddit.subreddit(
            self.config.subreddit_name
        )
        self.log.info("Starting watch of %s's mod log", subreddit)
        while not stop_event.is_set():
            try:
                async for modlog_entry in subreddit.mod.stream.log(
                    skip_existing=True, pause_after=10
                ):
                    # Break out of the for loop occasionally if there's nothing going on for a while
                    # to check if the stop_event is set.  modlog_entry will be None if pause_after is reached
                    if modlog_entry is None:
                        self.log.debug("Pausing modlog stream")
                        break

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
                        post: Submission = await self.config.reddit.submission(
                            id=target_name
                        )
                        await self.check_post_flair(post)

                    if (
                        modlog_entry.action == "wikirevise"
                        and modlog_entry.details
                        == f"Page {self.config.rules_wiki_page} edited"
                    ):
                        await self.config.update_rules()

                    if (
                        modlog_entry.details == "Ban Evasion"
                        and modlog_entry.mod == "reddit"
                    ):
                        if (
                            not self.config.rules
                            or not self.config.rules.general_settings.enable_flair_actions
                        ):
                            self.log.debug("Handling ban evadors is disabled")
                        else:
                            target_item: Comment | Submission | None = None
                            if modlog_entry.target_fullname[:2] == "t1":
                                target_item = await self.config.reddit.comment(
                                    id=modlog_entry.target_fullname[3:]
                                )
                            elif modlog_entry.target_fullname[:2] == "t3":
                                target_item = await self.config.reddit.submission(
                                    id=modlog_entry.target_fullname[3:]
                                )
                            else:
                                self.log.warning(
                                    "Unexpected target type for ban evasion: %s",
                                    modlog_entry.target_fullname,
                                )
                            if target_item is not None and target_item.author is not None:
                                await self.handle_ban_evasion(
                                    post=target_item, user=target_item.author
                                )

            except (RequestException, ServerError) as e:
                self.log.error("Server error in modlog watcher: %s.  Exiting.", e)
                stop_event.set()
                break
            except asyncio.CancelledError:
                self.log.info("Modlog watcher cancelled, exiting")
                stop_event.set()
                break
            except KeyboardInterrupt:
                self.log.info("Caught keyboard interrupt, exiting modlog watcher")
                stop_event.set()
                break
            except Exception as e:
                self.log.error("Error in modlog watcher: %s", e)
                stop_event.set()
                break
