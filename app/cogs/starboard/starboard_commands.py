import discord
from discord.ext import commands

from ...classes.bot import Bot


class Starboard(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.command(
        name='addStarboard', aliases=['add', 'as'],
        brief="Adds a starboard"
    )
    @commands.has_guild_permissions(manage_channels=True)
    async def add_starboard(
        self,
        ctx: commands.Context,
        channel: discord.TextChannel
    ) -> None:
        guild = await self.bot.get_sql_guild(ctx.guild.id)
        await guild.add_starboard(channel.id)
        await ctx.send(f"Added starboard {channel.mention}")


def setup(bot: Bot) -> None:
    bot.add_cog(Starboard(bot))
