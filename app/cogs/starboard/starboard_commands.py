from typing import Union

import discord
from discord.ext import commands

from ...classes.bot import Bot
from ... import utils
from ... import errors
from ... import converters


class Starboard(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.command(
        name='starboards', aliases=['s']
    )
    @commands.guild_only()
    async def list_starboards(
        self,
        ctx: commands.Context,
        starboard: converters.Starboard = None
    ) -> None:
        if starboard is None:
            starboards = await self.bot.db.get_starboards(ctx.guild.id)
            if len(starboards) == 0:
                await ctx.send(
                    "You do not have any starboards. "
                    "Add starboards with `sb!addStarboard "
                    "#channel`."
                )
                return

            embed = discord.Embed(
                title=f"Starboards for **{ctx.guild}**",
                description=(
                    "This lists the starboards and their "
                    "most important settings. To view all "
                    "settings, run `sb!starboards #starboard`."
                ),
                color=self.bot.theme_color
            )
            for s in starboards:
                c = ctx.guild.get_channel(s['id'])
                emoji_str = utils.pretty_emoji_string(
                    s['star_emojis'], ctx.guild)
                embed.add_field(
                    name=c.name,
                    value=(
                        f"emojis: {emoji_str}\n"
                        f"requiredStars: {s['required']}\n"
                    )
                )
            await ctx.send(embed=embed)
        else:
            s = starboard.sql_attributes
            upvote_emoji_str = utils.pretty_emoji_string(
                s['star_emojis'], ctx.guild)
            react_emoji_str = utils.pretty_emoji_string(
                s['react_emojis'], ctx.guild)
            embed = discord.Embed(
                title=starboard.obj.name,
                description=(
                    f"emojis: **{upvote_emoji_str}**\n"
                    f"reactEmojis: **{react_emoji_str}**\n"
                    f"displayEmoji: **{s['display_emoji']}**\n\n"
                    f"requiredStars: **{s['required']}**\n"
                    f"requiredToRemove: **{s['required_remove']}**\n"
                    f"selfStar: **{s['self_star']}**\n"
                    f"unstar: **{s['unstar']}**\n"
                    f"allowBots: **{s['allow_bots']}**\n"
                    f"linkDeletes: **{s['link_deletes']}**\n"
                    f"linkEdits: **{s['link_edits']}**\n"
                    f"imagesOnly: **{s['images_only']}**\n"
                    f"removeReactions: **{s['remove_reactions']}**\n"
                    f"noXp: **{s['no_xp']}**\n"
                    f"allowRandom: **{s['explore']}**"
                ),
                color=self.bot.theme_color
            )
            await ctx.send(embed=embed)

    @commands.command(
        name='addStarboard', aliases=['addsb', 'as', 'asb'],
        brief="Adds a starboard"
    )
    @commands.has_guild_permissions(manage_channels=True)
    async def add_starboard(
        self,
        ctx: commands.Context,
        channel: discord.TextChannel
    ) -> None:
        existed = await self.bot.db.create_starboard(channel.id, ctx.guild.id)
        if existed:
            raise errors.AlreadyExists(
                f"{channel.mention} is already a starboard."
            )
        else:
            await ctx.send(f"Created starboard {channel.mention}")

    @commands.command(
        name='removeStarboard', aliases=['removesb', 'rs', 'rsb'],
        brief="Removes a starboard"
    )
    @commands.has_guild_permissions(manage_channels=True)
    async def remove_starboard(
        self,
        ctx: commands.Context,
        channel: Union[discord.TextChannel, int]
    ) -> None:
        starboard = await self.bot.db.get_starboard(channel.id)
        if not starboard:
            raise errors.DoesNotExist(
                f"{channel.mention} is not a starboard."
            )
        else:
            await ctx.send(
                "Are you sure? All starboard messages will be lost."
            )
            confirmed = await utils.confirm(ctx)
            if confirmed is True:
                await self.bot.db.execute(
                    """DELETE FROM starboards WHERE id=$1""",
                    channel.id
                )
                await ctx.send(f"{channel.mention} is no longer a starboard.")
            if confirmed is False:
                await ctx.send("Cancelled.")


def setup(bot: Bot) -> None:
    bot.add_cog(Starboard(bot))
