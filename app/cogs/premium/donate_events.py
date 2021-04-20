import typing

from discord.ext import commands

if typing.TYPE_CHECKING:
    from app.classes.bot import Bot


class DonateEvents(commands.Cog):
    def __init__(self, bot: "Bot"):
        self.bot = bot

    @commands.Cog.listener()
    async def on_donatebot_event(self, data: dict, auth: str):
        print(data)
        print(auth)


def setup(bot: "Bot"):
    if 0 in bot.shard_ids:
        bot.add_cog(DonateEvents(bot))
