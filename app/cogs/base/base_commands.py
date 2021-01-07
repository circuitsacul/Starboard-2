from discord.ext import commands

from ...classes.bot import Bot
from ...classes.guild import Guild


class Base(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.command(
        name='test'
    )
    async def test(
        self,
        ctx: commands.Context
    ) -> None:
        guild = self.bot.cache.get_guild(ctx.guild.id)
        if guild is None:
            guild = await Guild.from_guild(self.bot, ctx.guild)
        await ctx.send(f"Starboards: {guild._starboards}")
        await ctx.send(f"Starboards: {await guild.starboards}")


def setup(bot: Bot) -> None:
    bot.add_cog(Base(bot))
