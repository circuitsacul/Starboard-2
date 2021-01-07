from typing import Union

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

    @commands.command(
        name='removeStarboard', aliases=['remove', 'rs'],
        brief="Removes a starboard"
    )
    @commands.has_guild_permissions(manage_channels=True)
    async def remove_starboard(
        self,
        ctx: commands.Context,
        channel: Union[discord.TextChannel, int]
    ) -> None:
        cid = channel if type(channel) is int else channel.id
        guild = await self.bot.get_sql_guild(ctx.guild.id)
        await guild.remove_starboard(cid)
        await ctx.send(f"Removed starboard **{channel}**")


def setup(bot: Bot) -> None:
    bot.add_cog(Starboard(bot))
