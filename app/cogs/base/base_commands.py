from discord.ext import commands

from ...bot import Bot
from ... import converters
from ...classes import starboard


class Base(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.command(
        name='test'
    )
    async def test(
        self,
        ctx: commands.Context,
        starboard_id: converters.Number
    ) -> None:
        await ctx.send(
            dir(await starboard.Starboard.from_id(self.bot, starboard_id))
        )


def setup(bot: Bot) -> None:
    bot.add_cog(Base(bot))
