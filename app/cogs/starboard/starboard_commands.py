from typing import Optional, Union

import discord
from discord.ext import commands

from app.classes.context import MyContext
from app.i18n import t_

from ... import converters, errors, menus, utils
from ...classes.bot import Bot


class Starboard(commands.Cog):
    "Manage starboards"

    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.group(
        name="starboards",
        aliases=["s"],
        help=t_("List starboards", True),
        invoke_without_command=True,
    )
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def starboards(
        self, ctx: "MyContext", starboard: converters.Starboard = None
    ) -> None:
        p = utils.escmd(ctx.prefix)
        if starboard is None:
            starboards = await self.bot.db.starboards.get_many(ctx.guild.id)
            if len(starboards) == 0:
                await ctx.send(
                    t_(
                        "You do not have any starboards. "
                        "Add starboards with `{0}s add "
                        "#channel`."
                    ).format(p)
                )
                return

            embed = discord.Embed(
                title=t_("Starboards for **{0}**:").format(ctx.guild),
                description=t_(
                    "This lists the starboards and their "
                    "most important settings. To view all "
                    "settings, run `{0}starboards #starboard`."
                ).format(p),
                color=self.bot.theme_color,
            )
            for s in starboards:
                c = ctx.guild.get_channel(s["id"])
                emoji_str = utils.pretty_emoji_string(
                    s["star_emojis"], ctx.guild
                )
                embed.add_field(
                    name=c.name
                    if c
                    else t_("Deleted Channel {0}").format(s["id"]),
                    value=(
                        f"emojis: **{emoji_str}**\n"
                        f"requiredStars: **{s['required']}**\n"
                    ),
                )
            await ctx.send(embed=embed)
        else:
            s = starboard.sql
            upvote_emoji_str = utils.pretty_emoji_string(
                s["star_emojis"], ctx.guild
            )
            embed = (
                discord.Embed(
                    title=starboard.obj.name,
                    color=self.bot.theme_color,
                )
                .add_field(
                    name="Appearance",
                    value=(
                        f"displayEmoji: **{s['display_emoji']}**\n"
                        f"color: **{s['color']}**\n"
                        f"useWebhook: **{s['use_webhook']}**\n"
                        f"username: **{s['webhook_name']}**\n"
                        + (
                            f"avatar: [view]({s['webhook_avatar']})\n"
                            if s["webhook_avatar"]
                            else "avatar: Default\n"
                        )
                    ),
                )
                .add_field(
                    name="Requirements",
                    value=(
                        f"emojis: **{upvote_emoji_str}**\n"
                        f"requiredStars: **{s['required']}**\n"
                        f"requiredRemove: **{s['required_remove']}**\n"
                        f"selfStar: **{s['self_star']}**\n"
                        f"allowBots: **{s['allow_bots']}**\n"
                        f"imagesOnly: **{s['images_only']}**\n"
                        f"regex: `{s['regex'] or 'None'}`\n"
                        f"excludeRegex: `{s['exclude_regex'] or 'None'}`\n"
                    ),
                )
                .add_field(
                    name="Behaviour",
                    value=(
                        f"ping: **{s['ping']}**\n"
                        f"autoReact: **{s['autoreact']}**\n"
                        f"linkDeletes: **{s['link_deletes']}**\n"
                        f"linkEdits: **{s['link_edits']}**\n"
                        f"removeInvalid: **{s['remove_invalid']}**\n"
                        f"noXp: **{s['no_xp']}**\n"
                        f"allowRandom: **{s['explore']}**\n"
                    ),
                )
            )
            await ctx.send(embed=embed)

    @starboards.command(
        name="webhook",
        aliases=["useWebhook"],
        help=t_(
            "Whether or not to use webhooks for starboard messages.", True
        ),
    )
    @commands.has_guild_permissions(manage_channels=True)
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def use_webhook(
        self,
        ctx: "MyContext",
        starboard: converters.Starboard,
        enable: converters.mybool,
    ):
        await self.bot.db.starboards.edit(
            starboard_id=starboard.obj.id, use_webhook=enable
        )
        await ctx.send(
            embed=utils.cs_embed(
                {"useWebhook": (starboard.sql["use_webhook"], enable)},
                bot=self.bot,
            )
        )

    @starboards.command(
        name="avatar",
        help=t_("Sets the avatar for webhook starboard messages.", True),
    )
    @commands.has_guild_permissions(manage_channels=True)
    @commands.guild_only()
    async def set_webhook_avatar(
        self,
        ctx: "MyContext",
        starboard: converters.Starboard,
        avatar_url: Optional[str] = None,
    ):
        if not starboard.sql["use_webhook"] and await menus.Confirm(
            t_(
                "This feature only works if `useWebhook` is enabled. "
                "Would you like to also enable this setting?"
            )
        ).start(ctx):
            await self.bot.db.starboards.edit(
                starboard.obj.id, use_webhook=True
            )
            await ctx.send(
                t_("Webhooks have been enabled for {0}.").format(
                    starboard.obj.mention
                )
            )
        await self.bot.db.starboards.set_webhook_avatar(
            starboard.obj.id, avatar_url
        )

        if avatar_url:
            await ctx.send(t_("Avatar set!"))
        else:
            await ctx.send(t_("Avatar reset to default."))

    @starboards.command(
        name="name",
        aliases=["username"],
        help=t_("Sets the username for webhook starboard messages.", True),
    )
    @commands.has_guild_permissions(manage_channels=True)
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def set_webhook_name(
        self,
        ctx: "MyContext",
        starboard: converters.Starboard,
        *,
        name: Optional[str] = None,
    ):
        enabled = False
        if not starboard.sql["use_webhook"] and await menus.Confirm(
            t_(
                "This feature only works if `useWebhook` is enabled. "
                "Would you like to also enable this setting?"
            )
        ).start(ctx):
            await self.bot.db.starboards.edit(
                starboard.obj.id, use_webhook=True
            )
            enabled = True
        await self.bot.db.starboards.set_webhook_name(starboard.obj.id, name)

        settings = {"webhookName": (starboard.sql["webhook_name"], name)}
        if enabled:
            settings["useWebhook"] = (False, True)

        await ctx.send(
            embed=utils.cs_embed(
                settings,
                self.bot,
            )
        )

    @starboards.command(
        name="add", aliases=["a"], help=t_("Adds a starboard", True)
    )
    @commands.has_guild_permissions(manage_channels=True)
    async def add_starboard(
        self, ctx: "MyContext", channel: discord.TextChannel
    ) -> None:
        existed = await self.bot.db.starboards.create(channel.id, ctx.guild.id)
        if existed:
            raise errors.AlreadyStarboard(channel.mention)
        else:
            await ctx.send(
                t_("Created starboard {0}.").format(channel.mention)
            )

    @starboards.command(
        name="remove",
        aliases=["delete", "del", "r"],
        help=t_("Removes a starboard", True),
    )
    @commands.has_guild_permissions(manage_channels=True)
    @commands.bot_has_permissions(
        add_reactions=True, read_message_history=True
    )
    @commands.guild_only()
    async def remove_starboard(
        self, ctx: "MyContext", channel: Union[discord.TextChannel, int]
    ) -> None:
        cid = channel.id if not isinstance(channel, int) else channel
        cname = channel.mention if not isinstance(channel, int) else channel
        starboard = await self.bot.db.starboards.get(cid)
        if not starboard:
            raise errors.NotStarboard(cname)
        else:
            confirmed = await menus.Confirm(
                t_("Are you sure? All starboard messages will be lost.")
            ).start(ctx)
            if confirmed is True:
                await self.bot.db.starboards.delete(cid)
                await ctx.send(
                    t_("{0} is no longer a starboard.").format(cname)
                )
            if confirmed is False:
                await ctx.send(t_("Cancelled."))

    @starboards.command(
        name="displayEmoji",
        aliases=["de"],
        help=t_("Set the emoji to show next to the points", True),
    )
    @commands.has_guild_permissions(manage_channels=True)
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def set_display_emoji(
        self,
        ctx: "MyContext",
        starboard: converters.Starboard,
        emoji: converters.Emoji,
    ) -> None:
        clean = utils.clean_emoji(emoji)
        await self.bot.db.starboards.edit(
            starboard.obj.id, display_emoji=clean
        )
        orig = utils.pretty_emoji_string(
            starboard.sql["display_emoji"], ctx.guild
        )
        await ctx.send(
            embed=utils.cs_embed({"displayEmoji": (orig, emoji)}, self.bot)
        )

    @starboards.command(
        name="color",
        aliases=["colour"],
        help=t_("Sets the embed color of starboard messages", True),
    )
    @commands.has_guild_permissions(manage_channels=True)
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def set_color(
        self,
        ctx: "MyContext",
        starboard: converters.Starboard,
        *,
        color: Optional[commands.ColorConverter],
    ) -> None:
        color = (
            str(color)
            if color
            else hex(self.bot.theme_color).replace("0x", "#")
        )

        await self.bot.db.starboards.edit(starboard.obj.id, color=color)
        await ctx.send(
            embed=utils.cs_embed(
                {"color": (starboard.sql["color"], color)}, self.bot
            )
        )

    @starboards.command(
        name="required",
        aliases=["requiredStars", "requiredPoints"],
        help=t_("Sets the number of reactions a message needs", True),
    )
    @commands.has_guild_permissions(manage_channels=True)
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def set_required(
        self,
        ctx: "MyContext",
        starboard: converters.Starboard,
        required: converters.myint,
    ) -> None:
        await self.bot.db.starboards.edit(starboard.obj.id, required=required)
        await ctx.send(
            embed=utils.cs_embed(
                {"required": (starboard.sql["required"], required)}, self.bot
            )
        )

    @starboards.command(
        name="requiredRemove",
        aliases=["rtm"],
        help=t_("How few stars a message has before it is removed", True),
    )
    @commands.has_guild_permissions(manage_channels=True)
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def set_required_remove(
        self,
        ctx: "MyContext",
        starboard: converters.Starboard,
        required_remove: converters.myint,
    ) -> None:
        await self.bot.db.starboards.edit(
            starboard.obj.id, required_remove=required_remove
        )
        await ctx.send(
            embed=utils.cs_embed(
                {
                    "requiredRemove": (
                        starboard.sql["required_remove"],
                        required_remove,
                    )
                },
                self.bot,
            )
        )

    @starboards.command(
        name="selfStar",
        aliases=["ss"],
        help=t_("Whether or not users can star their own messages", True),
    )
    @commands.has_guild_permissions(manage_channels=True)
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def set_self_star(
        self,
        ctx: "MyContext",
        starboard: converters.Starboard,
        self_star: converters.mybool,
    ) -> None:
        await self.bot.db.starboards.edit(
            starboard.obj.id, self_star=self_star
        )
        await ctx.send(
            embed=utils.cs_embed(
                {"selfStar": (starboard.sql["self_star"], self_star)}, self.bot
            )
        )

    @starboards.command(
        name="allowBots",
        aliases=["ab"],
        help=t_(
            "Whether or not bot messages can appear on the starboard", True
        ),
    )
    @commands.has_guild_permissions(manage_channels=True)
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def set_allow_Bots(
        self,
        ctx: "MyContext",
        starboard: converters.Starboard,
        allow_bots: converters.mybool,
    ) -> None:
        await self.bot.db.starboards.edit(
            starboard.obj.id, allow_bots=allow_bots
        )
        await ctx.send(
            embed=utils.cs_embed(
                {"allowBots": (starboard.sql["allow_bots"], allow_bots)},
                self.bot,
            )
        )

    @starboards.command(
        name="imagesOnly",
        aliases=["requireImage", "io"],
        help=t_("Whether messages must include an image", True),
    )
    @commands.has_guild_permissions(manage_channels=True)
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def set_images_only(
        self,
        ctx: "MyContext",
        starboard: converters.Starboard,
        images_only: converters.mybool,
    ) -> None:
        await self.bot.db.starboards.edit(
            starboard.obj.id, images_only=images_only
        )
        await ctx.send(
            embed=utils.cs_embed(
                {"imagesOnly": (starboard.sql["images_only"], images_only)},
                self.bot,
            )
        )

    @starboards.command(
        name="regex",
        aliases=["reg"],
        help=t_("A regex string that all messages must match", True),
    )
    @commands.has_guild_permissions(manage_channels=True)
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def set_regex(
        self,
        ctx: "MyContext",
        starboard: converters.Starboard,
        regex: Optional[str] = None,
    ) -> None:
        await self.bot.db.starboards.edit(starboard.obj.id, regex=regex)
        await ctx.send(
            embed=utils.cs_embed(
                {"regex": (starboard.sql["regex"], regex)}, self.bot
            )
        )

    @starboards.command(
        name="excludeRegex",
        aliases=["eregex", "ereg"],
        help=t_("A regex string that all messages must not match", True),
    )
    @commands.has_guild_permissions(manage_channels=True)
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def set_eregex(
        self,
        ctx: "MyContext",
        starboard: converters.Starboard,
        exclude_regex: Optional[str] = None,
    ) -> None:
        await self.bot.db.starboards.edit(
            starboard.obj.id, exclude_regex=exclude_regex
        )
        await ctx.send(
            embed=utils.cs_embed(
                {
                    "excludeRegex": (
                        starboard.sql["exclude_regex"],
                        exclude_regex,
                    )
                },
                self.bot,
            )
        )

    @starboards.command(
        name="ping",
        aliases=["mentionAuthor"],
        help=t_(
            "Whether or not to mention the author of a starboard message", True
        ),
    )
    @commands.has_guild_permissions(manage_channels=True)
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def set_ping(
        self,
        ctx: "MyContext",
        starboard: converters.Starboard,
        ping: converters.mybool,
    ) -> None:
        await self.bot.db.starboards.edit(starboard.obj.id, ping=ping)
        await ctx.send(
            embed=utils.cs_embed(
                {"ping": (starboard.sql["ping"], ping)}, self.bot
            )
        )

    @starboards.command(
        name="autoReact",
        aliases=["ar"],
        help=t_("Whether to automatically react to starboard messages", True),
    )
    @commands.has_guild_permissions(manage_channels=True)
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def set_auto_react(
        self,
        ctx: "MyContext",
        starboard: converters.Starboard,
        auto_react: converters.mybool,
    ) -> None:
        await self.bot.db.starboards.edit(
            starboard.obj.id, autoreact=auto_react
        )
        await ctx.send(
            embed=utils.cs_embed(
                {"autoReact": (starboard.sql["autoreact"], auto_react)},
                self.bot,
            )
        )

    @starboards.command(
        name="linkDeletes",
        aliases=["ld"],
        help=t_(
            "Whether to delete the starboard message if the original is", True
        ),
    )
    @commands.has_guild_permissions(manage_channels=True)
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def set_link_deletes(
        self,
        ctx: "MyContext",
        starboard: converters.Starboard,
        link_deletes: converters.mybool,
    ) -> None:
        await self.bot.db.starboards.edit(
            starboard.obj.id, link_deletes=link_deletes
        )
        await ctx.send(
            embed=utils.cs_embed(
                {"linkDeletes": (starboard.sql["link_deletes"], link_deletes)},
                self.bot,
            )
        )

    @starboards.command(
        name="linkEdits",
        aliases=["le"],
        help=t_(
            "Whether to update starboard messages with edited content", True
        ),
    )
    @commands.has_guild_permissions(manage_channels=True)
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def set_link_edits(
        self,
        ctx: "MyContext",
        starboard: converters.Starboard,
        link_edits: converters.mybool,
    ) -> None:
        await self.bot.db.starboards.edit(
            starboard.obj.id, link_edits=link_edits
        )
        await ctx.send(
            embed=utils.cs_embed(
                {"linkEdits": (starboard.sql["link_edits"], link_edits)},
                self.bot,
            )
        )

    @starboards.command(
        name="noXp",
        help=t_("Set to True to disable gaining XP for this starboard", True),
    )
    @commands.has_guild_permissions(manage_channels=True)
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def set_no_xp(
        self,
        ctx: "MyContext",
        starboard: converters.Starboard,
        no_xp: converters.mybool,
    ) -> None:
        await self.bot.db.starboards.edit(starboard.obj.id, no_xp=no_xp)
        await ctx.send(
            embed=utils.cs_embed(
                {"noXp": (starboard.sql["no_xp"], no_xp)}, self.bot
            )
        )

    @starboards.command(
        name="removeInvalid",
        aliases=["rmi", "rminvalid"],
        help=t_("Whether or not invalid reactions should be removed", True),
    )
    @commands.has_guild_permissions(manage_channels=True)
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def set_remove_invalid(
        self,
        ctx: "MyContext",
        starboard: converters.Starboard,
        remove_invalid: converters.mybool,
    ) -> None:
        await self.bot.db.starboards.edit(
            starboard.obj.id, remove_invalid=remove_invalid
        )
        await ctx.send(
            embed=utils.cs_embed(
                {
                    "removeInvalid": (
                        starboard.sql["remove_invalid"],
                        remove_invalid,
                    )
                },
                self.bot,
            )
        )

    @starboards.command(
        name="allowRandom",
        aliases=["rand", "explore"],
        help=t_(
            "Whether or not the random command can pull from this starboard",
            True,
        ),
    )
    @commands.has_guild_permissions(manage_channels=True)
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def set_allow_random(
        self,
        ctx: "MyContext",
        starboard: converters.Starboard,
        allow_random: converters.mybool,
    ) -> None:
        await self.bot.db.starboards.edit(
            starboard.obj.id, explore=allow_random
        )
        await ctx.send(
            embed=utils.cs_embed(
                {"allowRandom": (starboard.sql["explore"], allow_random)},
                self.bot,
            )
        )

    @starboards.group(
        name="starEmojis",
        aliases=["emojis", "se", "e"],
        help=t_("Modify starEmojis for a starboard", True),
        invoke_without_command=True,
    )
    @commands.has_guild_permissions(manage_channels=True)
    async def star_emojis(self, ctx: "MyContext") -> None:
        await ctx.send_help(ctx.command)

    @star_emojis.command(
        name="set", help=t_("Sets the starEmojis for a starboard", True)
    )
    @commands.has_guild_permissions(manage_channels=True)
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def set_star_emojis(
        self,
        ctx: "MyContext",
        starboard: converters.Starboard,
        *emojis: converters.Emoji,
    ) -> None:
        converted_emojis = [utils.clean_emoji(e) for e in emojis]
        original_emojis = starboard.sql["star_emojis"]

        await self.bot.db.starboards.edit(
            starboard.obj.id, star_emojis=converted_emojis
        )

        pretty_orig_emojis = utils.pretty_emoji_string(
            original_emojis, ctx.guild
        )
        pretty_new_emojis = utils.pretty_emoji_string(
            converted_emojis, ctx.guild
        )

        await ctx.send(
            embed=utils.cs_embed(
                {"starEmojis": (pretty_orig_emojis, pretty_new_emojis)},
                self.bot,
                noticks=True,
            )
        )

    @star_emojis.command(
        name="add", aliases=["a"], help=t_("Add a starEmoji", True)
    )
    @commands.has_guild_permissions(manage_channels=True)
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def add_star_emoji(
        self,
        ctx: "MyContext",
        starboard: converters.Starboard,
        emoji: converters.Emoji,
    ) -> None:
        converted_emoji = utils.clean_emoji(emoji)

        current_emojis = starboard.sql["star_emojis"]

        if converted_emoji in current_emojis:
            raise errors.AlreadySBEmoji(emoji, starboard.obj.mention)

        new_emojis = current_emojis + [converted_emoji]

        await self.bot.db.starboards.add_star_emoji(
            starboard.obj.id, emoji=converted_emoji
        )

        pretty_orig_emojis = utils.pretty_emoji_string(
            current_emojis, ctx.guild
        )
        pretty_new_emojis = utils.pretty_emoji_string(new_emojis, ctx.guild)

        await ctx.send(
            embed=utils.cs_embed(
                {"starEmojis": (pretty_orig_emojis, pretty_new_emojis)},
                self.bot,
                noticks=True,
            )
        )

    @star_emojis.command(
        name="remove",
        aliases=["r", "del"],
        help=t_("Removes a starEmoji", True),
    )
    @commands.has_guild_permissions(manage_channels=True)
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def remove_star_emoji(
        self,
        ctx: "MyContext",
        starboard: converters.Starboard,
        emoji: converters.Emoji,
    ) -> None:
        converted_emoji = utils.clean_emoji(emoji)

        current_emojis = starboard.sql["star_emojis"]

        if converted_emoji not in current_emojis:
            raise errors.NotSBEmoji(emoji, starboard.obj.mention)

        new_emojis = current_emojis.copy()
        new_emojis.remove(converted_emoji)

        await self.bot.db.starboards.remove_star_emoji(
            starboard.obj.id, emoji=converted_emoji
        )

        pretty_orig_emojis = utils.pretty_emoji_string(
            current_emojis, ctx.guild
        )
        pretty_new_emojis = utils.pretty_emoji_string(new_emojis, ctx.guild)

        await ctx.send(
            embed=utils.cs_embed(
                {"starEmojis": (pretty_orig_emojis, pretty_new_emojis)},
                self.bot,
                noticks=True,
            )
        )

    @star_emojis.command(
        name="clear",
        aliases=["removeAll"],
        help=t_("Clears all starEmojis for a starboard", True),
    )
    @commands.has_guild_permissions(manage_channels=True)
    @commands.bot_has_permissions(
        embed_links=True, add_reactions=True, read_message_history=True
    )
    @commands.guild_only()
    async def clear_star_emojis(
        self, ctx: "MyContext", starboard: converters.Starboard
    ) -> None:
        if not await menus.Confirm(
            t_("Are you sure you want to clear all emojis for {0}?").format(
                starboard.obj.mention
            )
        ).start(ctx):
            await ctx.send("Cancelled")
            return

        await self.bot.db.starboards.edit(starboard.obj.id, star_emojis=[])

        pretty_orig_emojis = utils.pretty_emoji_string(
            starboard.sql["star_emojis"], ctx.guild
        )
        pretty_new_emoijs = utils.pretty_emoji_string([], ctx.guild)

        await ctx.send(
            embed=utils.cs_embed(
                {"starEmojis": (pretty_orig_emojis, pretty_new_emoijs)},
                self.bot,
                noticks=True,
            )
        )


def setup(bot: Bot) -> None:
    bot.add_cog(Starboard(bot))
