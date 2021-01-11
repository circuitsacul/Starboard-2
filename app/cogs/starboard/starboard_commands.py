from typing import Union

import discord
from discord.ext import commands

from ...classes.bot import Bot


class Starboard(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.command(
        name='starboards', aliases=['s']
    )
    @commands.guild_only()
    async def list_starboards(
        self,
        ctx: commands.Context
    ) -> None:
        pass

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
        pass

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
        pass


def setup(bot: Bot) -> None:
    bot.add_cog(Starboard(bot))
