"""A module to react to private messages."""

import logging
import time
from os import PathLike

from asyncpraw.models import Subreddit
from asyncprawcore.exceptions import RequestException, ServerError

from rflying_tower_bot.config import BotConfig, dump_current_settings
from rflying_tower_bot.utilities import Utilities


class Inbox:
    """A class to react to new posts."""

    def __init__(self, config: BotConfig) -> None:
        """
        Create an instance of Inbox.

        Args:
        ----
            config (BotConfig): See config.BotConfig

        """
        self.log: logging.Logger = logging.getLogger(
            f"{__name__}.{self.__class__.__name__}"
        )
        self.config = config
        self.utilities = Utilities(config)

    @staticmethod
    async def do_dump_current_config(subreddit: Subreddit, path: PathLike) -> None:
        """
        Dump the current settings of the subreddit to a file.

        Args:
        ----
            subreddit (Subreddit): The subreddit object.
            path (PathLike): The path to the file where the settings will be dumped.

        Returns:
        -------
            None

        """
        await dump_current_settings(subreddit, str(path))

    async def watch_inbox(self) -> None:
        """Watch the private message inbox and react to new messages."""
        self.log.info("Watching the inbox for new messages")
        subreddit = await self.config.reddit.subreddit(self.config.subreddit_name)
        moderators = [moderator async for moderator in subreddit.moderator]
        while True:
            try:
                # Skip existing messages to avoid processing the same message multiple times
                # This is different from other streams, which do not skip existing items
                # The idea is that commands are more timely than other events, so commands sent
                # while the bot is offline probably shouldn't be done when the bot comes back online
                async for message in self.config.reddit.inbox.stream(
                    skip_existing=True
                ):
                    if (
                        not self.config.rules
                        or not self.config.rules.general_settings.enable_inbox_actions
                    ):
                        self.log.debug("Inbox actions disabled, skipping message")
                        continue

                    if message.author not in moderators:
                        self.log.info(
                            "Message from non-moderator %s: %s", message.author, message
                        )
                        continue

                    self.log.info(
                        "Message from moderator %s: %s", message.author, message
                    )

                    match message.subject:
                        case "dump_current_config":
                            self.log.info("Dumping config to file: %s", message.body)
                            try:
                                await self.do_dump_current_config(
                                    subreddit, message.body
                                )
                            except Exception as e:
                                self.log.error("Error dumping config: %s", e)
                            await message.mark_read()

                        case "reload_config":
                            self.log.info("Reloading config")
                            await self.config.update_rules()
                            await message.mark_read()

                        case _:
                            self.log.warning("Unknown command: %s", message.subject)

            except (RequestException, ServerError) as e:
                self.log.warning(
                    "Server error in post stream watcher: %s.  Sleeping for a bit.", e
                )
                # Yes, I know a blocking sleep in async code is bad, but if Reddit is having a problem might as well pause the whole bot
                time.sleep(60)
            except KeyboardInterrupt:
                self.log.info("Caught keyboard interrupt, exiting inbox watcher")
                break
            except Exception as e:
                self.log.error("Error in inbox watcher: %s", e)
