import discord
from discord.ext import commands

from app.classes.bot import Bot
from app import converters
from app import utils


class AutoStarChannels(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.group(
        name="aschannels",
        aliases=["autostarchannels", "asc"],
        brief="List AutoStar Channels",
        invoke_without_command=True,
    )
    @commands.guild_only()
    async def aschannels(
        self, ctx: commands.Context, aschannel: converters.ASChannel = None
    ) -> None:
        """Lists all AutoStarChannels, or shows settings for a
        specific AutoStarChannel."""
        if not aschannel:
            p = utils.escmd(ctx.prefix)
            aschannels = await self.bot.db.get_aschannels(ctx.guild.id)

            if len(aschannels) == 0:
                await ctx.send(
                    "You do not have any AutoStarChannels. use "
                    f"`{p}asc add <channel>` to create one."
                )
                return

            embed = discord.Embed(
                title="AutoStarChannels",
                description=(
                    "This lists all AutoStarChannels and their most "
                    f"important settings. Use `{p}asc <aschannel>` to "
                    "view all settings."
                ),
                color=self.bot.theme_color,
            )
            for asc in aschannels:
                c = ctx.guild.get_channel(int(asc["id"]))
                emoji_str = utils.pretty_emoji_string(asc["emojis"], ctx.guild)
                embed.add_field(
                    name=c or f"Deleted Channel {asc['id']}",
                    value=(
                        f"emojis: **{emoji_str}**\n"
                        f"minChars: **{asc['min_chars']}**\n"
                        f"requireImage: **{asc['require_image']}**\n"
                    ),
                )

            await ctx.send(embed=embed)
        else:
            a = aschannel.sql_attributes
            c = aschannel.obj
            emoji_str = utils.pretty_emoji_string(a["emojis"], ctx.guild)
            embed = discord.Embed(
                title=f"{c.name}",
                description=(
                    f"emojis: **{emoji_str}**\n"
                    f"minChars: **{a['min_chars']}**\n"
                    f"requireImage: **{a['require_image']}**\n"
                    f"deleteInvalid: **{a['delete_invalid']}**\n"
                    f"regex: `{utils.escmd(a['regex']) or 'None'}`\n"
                    "excludeRegex: "
                    f"`{utils.escmd(a['exclude_regex']) or 'None'}`"
                ),
                color=self.bot.theme_color,
            )
            await ctx.send(embed=embed)

    @aschannels.command(
        name="add", aliases=["a", "+"], brief="Adds an AutoStarChannel"
    )
    @commands.has_guild_permissions(manage_channels=True)
    async def add_aschannel(
        self, ctx: commands.Context, channel: discord.TextChannel
    ) -> None:
        """Creates an AutoStarChannel"""
        await self.bot.db.create_aschannel(channel.id, ctx.guild.id)
        await ctx.send(f"Created AutoStarChannel {channel.mention}")

    @aschannels.command(
        name="remove", aliases=["r", "-"], brief="Removes an AutoStarChannel"
    )
    @commands.has_guild_permissions(manage_channels=True)
    async def remove_aschannel(
        self, ctx: commands.Context, aschannel: converters.ASChannel
    ) -> None:
        """Deletes an AutoStarChannel"""
        await self.bot.db.execute(
            """DELETE FROM aschannels
            WHERE id=$1""",
            aschannel.obj.id,
        )
        await ctx.send(f"Deleted AutoStarChannel {aschannel.obj.mention}.")


def setup(bot: Bot) -> None:
    bot.add_cog(AutoStarChannels(bot))
