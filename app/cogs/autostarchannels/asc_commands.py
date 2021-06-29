from typing import Optional

import discord
from discord.ext.prettyhelp import bot_has_permissions, has_guild_permissions

from app import buttons, commands, converters, errors, utils
from app.classes.bot import Bot
from app.classes.context import MyContext
from app.i18n import t_


class AutoStarChannels(
    commands.Cog, description=t_("Manage AutoStar channels.", True)
):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.group(
        name="aschannels",
        aliases=["autostarchannels", "asc"],
        help=t_(
            "List AutoStar Channels, or show "
            "settings for a specific AutoStar channel.",
            True,
        ),
        invoke_without_command=True,
    )
    @bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def aschannels(
        self, ctx: "MyContext", aschannel: converters.ASChannel = None
    ) -> None:
        if not aschannel:
            p = utils.escmd(ctx.prefix)
            aschannels = await self.bot.db.aschannels.get_many(ctx.guild.id)

            if len(aschannels) == 0:
                await ctx.send(
                    t_(
                        "You do not have any AutoStar channels. Use "
                        "`{0}asc add <channel>` to create one."
                    ).format(p)
                )
                return

            embed = discord.Embed(
                title=t_("AutoStar channels"),
                description=t_(
                    "This lists all AutoStar channels and their most "
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
        name="add",
        aliases=["a", "+"],
        help=t_("Adds an AutoStar channel.", True),
    )
    @has_guild_permissions(manage_channels=True)
    async def add_aschannel(
        self, ctx: "MyContext", channel: discord.TextChannel
    ) -> None:
        await self.bot.db.aschannels.create(channel.id, ctx.guild.id)
        await ctx.send(
            t_("Created AutoStar channel {0}.").format(channel.mention)
        )

    @aschannels.command(
        name="remove",
        aliases=["r", "-"],
        help=t_("Removes an AutoStar channel.", True),
    )
    @has_guild_permissions(manage_channels=True)
    async def remove_aschannel(
        self, ctx: "MyContext", aschannel: converters.ASChannel
    ) -> None:
        await self.bot.db.aschannels.delete(aschannel.obj.id)
        await ctx.send(
            t_("Deleted AutoStar channel {0}.").format(aschannel.obj.mention)
        )

    @aschannels.group(
        name="emojis",
        aliases=["e"],
        help=t_("Modify the emojis for AutoStar channels.", True),
        invoke_without_command=True,
    )
    @has_guild_permissions(manage_channels=True)
    async def asemojis(self, ctx: "MyContext") -> None:
        await ctx.send_help(ctx.command)

    @asemojis.command(
        name="set", help=t_("Sets the emojis for an AutoStar channel.", True)
    )
    @has_guild_permissions(manage_channels=True)
    @bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def set_asemojis(
        self,
        ctx: "MyContext",
        aschannel: converters.ASChannel,
        *emojis: converters.Emoji,
    ) -> None:
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
        name="add",
        aliases=["a"],
        help=t_("Adds an emoji to an AutoStar channel.", True),
    )
    @has_guild_permissions(manage_channels=True)
    @bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def add_asemoji(
        self,
        ctx: "MyContext",
        aschannel: converters.ASChannel,
        emoji: converters.Emoji,
    ) -> None:
        clean = utils.clean_emoji(emoji)
        try:
            await self.bot.db.aschannels.add_asemoji(aschannel.obj.id, clean)
        except errors.AlreadyASEmoji:
            raise errors.AlreadyASEmoji(emoji, aschannel.obj.mention)
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
        help=t_("Removes an emoji from an AutoStar channel.", True),
    )
    @has_guild_permissions(manage_channels=True)
    @bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def remove_asemoji(
        self,
        ctx: "MyContext",
        aschannel: converters.ASChannel,
        emoji: converters.Emoji,
    ) -> None:
        clean = utils.clean_emoji(emoji)
        try:
            await self.bot.db.aschannels.remove_asemojis(
                aschannel.obj.id, clean
            )
        except errors.NotASEmoji:
            raise errors.NotASEmoji(emoji, aschannel.obj.mention)
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
        help=t_("Removes all emojis from an AutoStar channel.", True),
    )
    @has_guild_permissions(manage_channels=True)
    @bot_has_permissions(embed_links=True, read_message_history=True)
    @commands.guild_only()
    async def clear_asemojis(
        self, ctx: "MyContext", aschannel: converters.ASChannel
    ) -> None:
        if not await buttons.Confirm(
            ctx,
            t_("Are you sure you want to clear all emojis for {0}?").format(
                aschannel.obj.mention
            ),
        ).start():
            await ctx.send("Cancelled.")
            return

        await self.bot.db.aschannels.edit(aschannel.obj.id, emojis=[])
        old = utils.pretty_emoji_string(aschannel.sql["emojis"], ctx.guild)
        await ctx.send(
            embed=utils.cs_embed(
                {"emojis": (old, "None")}, self.bot, noticks=True
            )
        )

    @aschannels.command(
        name="minChars",
        aliases=["min", "mc"],
        help=t_("Sets the minimum number of characters for messages.", True),
    )
    @has_guild_permissions(manage_channels=True)
    @bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def set_min_chars(
        self,
        ctx: "MyContext",
        aschannel: converters.ASChannel,
        min_chars: converters.myint,
    ) -> None:
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
        help=t_("Whether or not messages must include an image.", True),
    )
    @has_guild_permissions(manage_channels=True)
    @bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def set_require_image(
        self,
        ctx: "MyContext",
        aschannel: converters.ASChannel,
        require_image: converters.mybool,
    ) -> None:
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
        help=t_("A regex string that all messages must match.", True),
    )
    @has_guild_permissions(manage_channels=True)
    @bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def set_regex(
        self,
        ctx: "MyContext",
        aschannel: converters.ASChannel,
        regex: Optional[str] = None,
    ) -> None:
        await self.bot.db.aschannels.edit(aschannel.obj.id, regex=regex)
        await ctx.send(
            embed=utils.cs_embed(
                {"regex": (aschannel.sql["regex"], regex)}, self.bot
            )
        )

    @aschannels.command(
        name="excludeRegex",
        alaises=["eregex", "ereg"],
        help=t_("A regex string that all messages must not match.", True),
    )
    @has_guild_permissions(manage_channels=True)
    @bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def set_eregex(
        self,
        ctx: "MyContext",
        aschannel: converters.ASChannel,
        exclude_regex: Optional[str] = None,
    ) -> None:
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
        help=t_("Whether or not to delete invalid messages.", True),
    )
    @has_guild_permissions(manage_channels=True)
    @bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def set_delete_invalid(
        self,
        ctx: "MyContext",
        aschannel: converters.ASChannel,
        delete_invalid: converters.mybool,
    ) -> None:
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
