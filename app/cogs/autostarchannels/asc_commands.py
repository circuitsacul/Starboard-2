import discord
from discord.ext import commands

from app import converters, errors, utils, menus
from app.classes.bot import Bot
from app.i18n import t_


class AutoStarChannels(commands.Cog):
    """Manage AutoStarChannels"""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.group(
        name="aschannels",
        aliases=["autostarchannels", "asc"],
        brief="List AutoStar Channels",
        invoke_without_command=True,
    )
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def aschannels(
        self, ctx: commands.Context, aschannel: converters.ASChannel = None
    ) -> None:
        """Lists all AutoStarChannels, or shows settings for a
        specific AutoStarChannel."""
        if not aschannel:
            p = utils.escmd(ctx.prefix)
            aschannels = await self.bot.db.aschannels.get_many(ctx.guild.id)

            if len(aschannels) == 0:
                await ctx.send(
                    t_(
                        "You do not have any AutoStarChannels. use "
                        "`{0}asc add <channel>` to create one."
                    ).format(p)
                )
                return

            embed = discord.Embed(
                title="AutoStarChannels",
                description=t_(
                    "This lists all AutoStarChannels and their most "
                    "important settings. Use `{0}asc <aschannel>` to "
                    "view all settings."
                ).format(p),
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
            a = aschannel.sql
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
        await self.bot.db.aschannels.create(channel.id, ctx.guild.id)
        await ctx.send(
            t_("Created AutoStarChannel {0.mention}").format(channel)
        )

    @aschannels.command(
        name="remove", aliases=["r", "-"], brief="Removes an AutoStarChannel"
    )
    @commands.has_guild_permissions(manage_channels=True)
    async def remove_aschannel(
        self, ctx: commands.Context, aschannel: converters.ASChannel
    ) -> None:
        """Deletes an AutoStarChannel"""
        await self.bot.db.aschannels.delete(aschannel.obj.id)
        await ctx.send(
            t_("Deleted AutoStarChannel {0.obj.mention}.").format(aschannel)
        )

    @aschannels.group(
        name="emojis",
        aliases=["e"],
        brief="Modify the emojis for AutoStarChannels",
        invoke_without_command=True,
    )
    @commands.has_guild_permissions(manage_channels=True)
    async def asemojis(self, ctx: commands.Context) -> None:
        p = utils.clean_prefix(ctx)
        await ctx.send(
            t_(
                "Options:\n```"
                " - {0}asc emojis add <aschannel> <emoji>\n"
                " - {0}asc emojis remove <aschannel> <emoji>\n"
                " - {0}asc emojis clear <aschannel>\n"
                " - {0}asc emojis set <aschannel> [emoji1, emoji2]```"
            ).format(p)
        )

    @asemojis.command(
        name="set", brief="Sets the emojis for an AutoStarChannel"
    )
    @commands.has_guild_permissions(manage_channels=True)
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def set_asemojis(
        self,
        ctx: commands.Context,
        aschannel: converters.ASChannel,
        *emojis: converters.Emoji,
    ) -> None:
        """Accepts a list of emojis to replace the original emojis with
        on an AutoStarChannel."""
        converted_emojis = [utils.clean_emoji(e) for e in emojis]

        await self.bot.db.aschannels.edit(
            aschannel.obj.id, emojis=converted_emojis
        )

        old = utils.pretty_emoji_string(aschannel.sql["emojis"], ctx.guild)
        new = utils.pretty_emoji_string(converted_emojis, ctx.guild)

        await ctx.send(
            embed=utils.cs_embed(
                {"emojis": (old, new)}, self.bot, noticks=True
            )
        )

    @asemojis.command(
        name="add", aliases=["a"], brief="Adds an emoji to an AutoStarChannel"
    )
    @commands.has_guild_permissions(manage_channels=True)
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def add_asemoji(
        self,
        ctx: commands.Context,
        aschannel: converters.ASChannel,
        emoji: converters.Emoji,
    ) -> None:
        """Adds an emoji to an AutoStarChannel, so messages sent
        there will automatically receive this as a reaction from
        Starboard."""
        clean = utils.clean_emoji(emoji)
        try:
            await self.bot.db.aschannels.add_asemoji(aschannel.obj.id, clean)
        except errors.AlreadyExists:
            # Raise a more user-friendly error message
            raise errors.AlreadyExists(
                f"{emoji} is already an emoji on {aschannel.obj.mention}"
            )
        old = utils.pretty_emoji_string(aschannel.sql["emojis"], ctx.guild)
        new = utils.pretty_emoji_string(
            aschannel.sql["emojis"] + [emoji], ctx.guild
        )
        await ctx.send(
            embed=utils.cs_embed(
                {"emojis": (old, new)}, self.bot, noticks=True
            )
        )

    @asemojis.command(
        name="remove",
        aliases=["r", "d", "del", "delete"],
        brief="Removes an emojis from an AutoStarChannel",
    )
    @commands.has_guild_permissions(manage_channels=True)
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def remove_asemoji(
        self,
        ctx: commands.Context,
        aschannel: converters.ASChannel,
        emoji: converters.Emoji,
    ) -> None:
        """Removes an emoji from an AutoStarChannel"""
        clean = utils.clean_emoji(emoji)
        try:
            await self.bot.db.aschannels.remove_asemojis(
                aschannel.obj.id, clean
            )
        except errors.DoesNotExist:
            raise errors.DoesNotExist(
                f"{emoji} is not an emoji on {aschannel.obj.mention}"
            )
        _new = aschannel.sql["emojis"]
        old = utils.pretty_emoji_string(aschannel.sql["emojis"], ctx.guild)
        _new.remove(clean)
        new = utils.pretty_emoji_string(_new, ctx.guild)
        await ctx.send(
            embed=utils.cs_embed(
                {"emojis": (old, new)}, self.bot, noticks=True
            )
        )

    @asemojis.command(
        name="clear",
        aliases=["reset"],
        brief="Removes all emojis from an AutoStarChannel",
    )
    @commands.has_guild_permissions(manage_channels=True)
    @commands.bot_has_permissions(embed_links=True, read_message_history=True)
    @commands.guild_only()
    async def clear_asemojis(
        self, ctx: commands.Context, aschannel: converters.ASChannel
    ) -> None:
        """Removes all emojis from an AutoStarChannel"""
        if not await menus.Confirm(
            t_(
                "Are you sure you want to clear all emojis " "for {0.mention}?"
            ).format(aschannel)
        ).start(ctx):
            await ctx.send("Cancelled")
            return

        await self.bot.db.aschannels.edit(aschannel.obj.id, emojis=[])
        old = utils.pretty_emoji_string(aschannel.sql["emojis"], ctx.guild)
        await ctx.send(
            embed=utils.cs_embed({"emojis": (old, "None")}, self.bot)
        )

    @aschannels.command(
        name="minChars",
        aliases=["min", "mc"],
        brief="The minimum number of characters for messages",
    )
    @commands.has_guild_permissions(manage_channels=True)
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def set_min_chars(
        self,
        ctx: commands.Context,
        aschannel: converters.ASChannel,
        min_chars: converters.myint,
    ) -> None:
        """Sets the minChars setting for an AutoStarChannel.

        All messages must be at least this many characters long
        in order for them to be autoreacted to."""
        await self.bot.db.aschannels.edit(
            aschannel.obj.id, min_chars=min_chars
        )
        await ctx.send(
            embed=utils.cs_embed(
                {"minChars": (aschannel.sql["min_chars"], min_chars)}, self.bot
            )
        )

    @aschannels.command(
        name="requireImage",
        aliases=["imagesOnly", "ri"],
        brief="Whether or not messages must include an image",
    )
    @commands.has_guild_permissions(manage_channels=True)
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def set_require_image(
        self,
        ctx: commands.Context,
        aschannel: converters.ASChannel,
        require_image: converters.mybool,
    ) -> None:
        """Sets the imagesOnly setting for an AutoStarChannel.

        All messages must include an uploaded attachment in order
        for them to be autoreacted to. This does not include links
        to images."""
        await self.bot.db.aschannels.edit(
            aschannel.obj.id, require_image=require_image
        )
        await ctx.send(
            embed=utils.cs_embed(
                {
                    "requireImage": (
                        aschannel.sql["require_image"],
                        require_image,
                    )
                },
                self.bot,
            )
        )

    @aschannels.command(
        name="regex",
        aliases=["reg"],
        brief="A regex string that all messages must match",
    )
    @commands.has_guild_permissions(manage_channels=True)
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def set_regex(
        self,
        ctx: commands.Context,
        aschannel: converters.ASChannel,
        regex: str,
    ) -> None:
        """Sets the regex setting for an AutoStarChannel.

        All messages must match this regex string in order to be
        autoreacted to. If the regex string takes longer than 0.01
        seconds, the bot will assume success and will send a
        warning to your log channel."""
        await self.bot.db.aschannels.edit(aschannel.obj.id, regex=regex)
        await ctx.send(
            embed=utils.cs_embed(
                {"regex": (aschannel.sql["regex"], regex)}, self.bot
            )
        )

    @aschannels.command(
        name="excludeRegex",
        alaises=["eregex", "ereg"],
        brief="A regex string that all messages must not match",
    )
    @commands.has_guild_permissions(manage_channels=True)
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def set_eregex(
        self,
        ctx: commands.Context,
        aschannel: converters.ASChannel,
        exclude_regex: str,
    ) -> None:
        """Sets the excludeRegex setting for an AutoStarChannel.

        All messages must NOT match this regex string in order
        to be autoreacted to. If the regex string takes longer than
        0.01 seconds, the bot will assume that it did not match
        (success) and will send a warning to your log channel."""
        await self.bot.db.aschannels.edit(
            aschannel.obj.id, exclude_regex=exclude_regex
        )
        await ctx.send(
            embed=utils.cs_embed(
                {
                    "excludeRegex": (
                        aschannel.sql["exclude_regex"],
                        exclude_regex,
                    )
                },
                self.bot,
            )
        )

    @aschannels.command(
        name="deleteInvalid",
        aliases=["di"],
        brief="Whether or not to delete invalid messages",
    )
    @commands.has_guild_permissions(manage_channels=True)
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def set_delete_invalid(
        self,
        ctx: commands.Context,
        aschannel: converters.ASChannel,
        delete_invalid: converters.mybool,
    ) -> None:
        """Sets the deleteInvalid setting for an AutoStarChannel.

        If this is set to True, any messages that do not meet
        the requirements of of the AutoStarChannel will be deleted.
        If it is set to False, then the bot will simply ignore them."""
        await self.bot.db.aschannels.edit(
            aschannel.obj.id, delete_invalid=delete_invalid
        )
        await ctx.send(
            embed=utils.cs_embed(
                {
                    "deleteInvalid": (
                        aschannel.sql["delete_invalid"],
                        delete_invalid,
                    )
                },
                self.bot,
            )
        )


def setup(bot: Bot) -> None:
    bot.add_cog(AutoStarChannels(bot))
