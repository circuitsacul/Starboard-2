from typing import Union

import discord
from discord.ext import commands, flags

from ... import converters, errors, utils
from ...classes.bot import Bot


OPTION_MAP = {
    'required': 'required',
    'required_remove': 'requiredRemove',
    'self_star': 'selfStar',
    'unstar': 'allowUnstar',
    'allow_bots': 'allowBots',
    'link_deletes': 'linkDeletes',
    'link_edits': 'linkEdits',
    'images_only': 'imagesOnly',
    'remove_reactions': 'removeReactions',
    'no_xp': 'noXp',
    'explore': 'allowRandom',
    'star_emojis': 'starEmojis',
    'react_emojis': 'reactEmojis',
    'display_emoji': 'displayEmoji'
}


class Starboard(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.group(
        name='starboards', aliases=['s'],
        brief="List starboards",
        invoke_without_command=True
    )
    @commands.guild_only()
    async def starboards(
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

    @starboards.command(
        name='add', aliases=['a'],
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

    @starboards.command(
        name='remove', aliases=['delete', 'del', 'r'],
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

    @flags.add_flag('--required', '-r', type=converters.myint)
    @flags.add_flag('--requiredRemove', '-rtl', type=converters.myint)
    @flags.add_flag('--selfStar', '-ss', type=converters.mybool)
    @flags.add_flag('--allowUnstar', '--unstar', '-us', type=converters.mybool)
    @flags.add_flag('--allowBots', '-ab', type=converters.mybool)
    @flags.add_flag('--linkDeletes', '-ld', type=converters.mybool)
    @flags.add_flag('--linkEdits', '-le', type=converters.mybool)
    @flags.add_flag('--imagesOnly', '-ri', '-io', type=converters.mybool)
    @flags.add_flag('--removeReactions', '-rr', type=converters.mybool)
    @flags.add_flag('--noXp', '-nxp', type=converters.mybool)
    @flags.add_flag(
        '--allowRandom', '--random', '-e',
        type=converters.mybool
    )
    @starboards.command(
        cls=flags.FlagCommand,
        name='settings', aliases=['cs', 'options', 'config'],
        brief="Change settings for a starboard"
    )
    async def set_starboard_settings(
        self,
        ctx: commands.Context,
        starboard: converters.Starboard,
        **options: dict
    ) -> None:
        """Configure the default options for a starboard.

        Usage:
            sb!s cs <starboard> **options

        Examples:
            Set requiredStars to 0 for #starboard:
            sb!s cs #starboard --required 0

            Set selfStar and allowRandom to False for #starboard:
            sb!s cs #starboard --allowRandom False --selfStar False

        All options:
            --required
            --requiredRemove
            --selfStar
            --allowUnstar
            --allowBots
            --linkDeletes
            --linkEdits
            --imagesOnly
            --removeReactions
            --noXp"""
        await self.bot.db.edit_starboard(
            starboard.obj.id,
            options['required'],
            options['requiredRemove'],
            options['selfStar']
        )

        changes = ""
        for option, value in starboard.sql_attributes.items():
            pretty_option = OPTION_MAP.get(option)
            if pretty_option is None:
                continue
            new_val = options.get(OPTION_MAP[option])
            if new_val is None:
                continue
            changes += (
                f"{OPTION_MAP[option]}: **{value}** "
                f":arrow_right: **{new_val}**\n"
            )

        if len(changes) == 0:
            changes = "No updated settings"

        embed = discord.Embed(
            title=f"Updated Settings for {starboard.obj.name}",
            description=changes,
            color=self.bot.theme_color
        )
        await ctx.send(embed=embed)


def setup(bot: Bot) -> None:
    bot.add_cog(Starboard(bot))
