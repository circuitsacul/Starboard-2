import discord
from discord.ext import commands

from app.classes.bot import Bot
from app import converters


class AutoStarChannels(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.group(
        name="aschannels", aliases=["autostarchannels", "asc"],
        brief="List AutoStar Channels",
        invoke_without_command=True
    )
    @commands.guild_only()
    async def aschannels(
        self, ctx: commands.Context,
        aschannel: converters.ASChannel = None
    ) -> None:
        if not aschannel:
            aschannels = await self.bot.db.get_aschannels(ctx.guild.id)
            await ctx.send(aschannels)
        else:
            await ctx.send(aschannel.sql_attributes)

    @aschannels.command(
        name="add", aliases=["a", "+"],
        brief="Adds an AutoStarChannel"
    )
    @commands.has_guild_permissions(manage_channels=True)
    async def add_aschannel(
        self, ctx: commands.Context, channel: discord.TextChannel
    ) -> None:
        await self.bot.db.create_aschannel(
            channel.id, ctx.guild.id
        )
        await ctx.send(f"Created AutoStarChannel {channel.mention}")

    @aschannels.command(
        name="remove", aliases=["r", "-"],
        brief="Removes an AutoStarChannel"
    )
    @commands.has_guild_permissions(manage_channels=True)
    async def remove_aschannel(
        self, ctx: commands.Context, aschannel: converters.ASChannel
    ) -> None:
        await self.bot.db.execute(
            """DELETE FROM aschannels
            WHERE id=$1""", aschannel.obj.id
        )
        await ctx.send(f"Deleted AutoStarChannel {aschannel.obj.mention}.")


def setup(bot: Bot) -> None:
    bot.add_cog(AutoStarChannels(bot))
