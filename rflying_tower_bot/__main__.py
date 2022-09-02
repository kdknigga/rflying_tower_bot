import asyncio
import logging

import asyncpraw

from .config import BotConfig, PRAWConfig
from .modlog import ModLog

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

log: logging.Logger = logging.getLogger(f"{__name__}")

praw_config = PRAWConfig()


async def main() -> None:
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

        await bot_config.update_rules()

        modlog = ModLog(bot_config)

        # The gather here is currently unnessisary, but is here to be ready for when
        # we want to watch things other than the modlog.
        await asyncio.gather(modlog.watch_modlog())


asyncio.run(main())
