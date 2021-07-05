from typing import TYPE_CHECKING

from discord.ext import tasks

import config
from app import commands

if TYPE_CHECKING:
    from app.classes.bot import Bot


class BotBlockStats(commands.Cog):
    def __init__(self, bot: "Bot"):
        self.bot = bot
        if 0 in self.bot.shard_ids and not config.DEVELOPMENT:
            self.post_stats.start()

    @tasks.loop(minutes=30)
    async def post_stats(self):
        await self.bot.wait_until_ready()
        params = {
            "server_count": sum(
                [s["guilds"] for _, s in self.bot.stats.items()]
            ),
            "bot_id": self.bot.user.id,
            **config.BOT_LISTS,
        }
        async with self.bot.session.post(
            "https://botblock.org/api/count", data=params
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()
            print(data)


def setup(bot: "Bot"):
    bot.add_cog(BotBlockStats(bot))
