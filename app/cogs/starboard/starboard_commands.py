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
        guild = await self.bot.get_sql_guild(ctx.guild.id)
        starboards = await guild.starboards

        if len(starboards) == 0:
            await ctx.send(
                "No starboards have been set. "
                "Use `sb!add #channel` to add one."
            )
            return

        description = ""
        for s in starboards:
            if s.channel is None:
                name = f"Deleted Channel `{s.id}`"
            else:
                name = s.channel.mention
            description += f"{name} {''.join(s.star_emojis)}"
            if s is not starboards[-1]:
                description += '\n'

        embed = discord.Embed(
            title="Starboards",
            description=description,
            color=self.bot.theme_color
        )

        await ctx.send(embed=embed)

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
