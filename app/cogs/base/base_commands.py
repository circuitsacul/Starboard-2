import discord
from discord.ext import commands

from ...classes.bot import Bot


class Base(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.command(
        name='test'
    )
    async def test(
        self,
        ctx: commands.Context,
        starboard: discord.TextChannel
    ) -> None:
        guild = await self.bot.get_sql_guild(ctx.guild.id)
        await ctx.send(await guild.get_starboard(starboard.id))


def setup(bot: Bot) -> None:
    bot.add_cog(Base(bot))
