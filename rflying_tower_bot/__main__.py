"""The main entry point for the bot."""

import asyncio
import logging

import asyncpraw

from rflying_tower_bot.config import BotConfig, PRAWConfig
from rflying_tower_bot.modlog import ModLog
from rflying_tower_bot.post_stream import PostStream

log: logging.Logger = logging.getLogger(f"{__name__}")

praw_config = PRAWConfig()


async def main() -> None:
    """Initialize the bot, grab the rules, and start any event loops."""
    async with asyncpraw.Reddit(
        client_id=praw_config.client_id,
        client_secret=praw_config.client_secret,
        user_agent=praw_config.client_user_agent,
        username=praw_config.username,
        password=praw_config.password,
        ratelimit_seconds=600,
        timeout=30,
        validate_on_submit=True,
    ) as reddit:
        bot_config = BotConfig(reddit)

        await bot_config.history.initialize_db()

        await bot_config.update_rules()

        modlog = ModLog(bot_config)
        post_stream = PostStream(bot_config)

        await asyncio.gather(modlog.watch_modlog(), post_stream.watch_poststream())


try:
    asyncio.run(main())
except KeyboardInterrupt:
    pass
