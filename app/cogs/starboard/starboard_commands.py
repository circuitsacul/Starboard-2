from typing import Union

import discord
from discord.ext import commands

from ... import converters, errors, utils
from ...classes.bot import Bot


class Starboard(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.group(
        name="starboards",
        aliases=["s"],
        brief="List starboards",
        invoke_without_command=True,
    )
    @commands.guild_only()
    async def starboards(
        self, ctx: commands.Context, starboard: converters.Starboard = None
    ) -> None:
        """Lists all starboards, and shows the important
        settings. All settings can be viewed by running
        sb!starboards <starboard>"""
        p = utils.escmd(ctx.prefix)
        if starboard is None:
            starboards = await self.bot.db.starboards.get_many(ctx.guild.id)
            if len(starboards) == 0:
                await ctx.send(
                    "You do not have any starboards. "
                    f"Add starboards with `{p}s add "
                    "#channel`."
                )
                return

            embed = discord.Embed(
                title=f"Starboards for **{ctx.guild}**",
                description=(
                    "This lists the starboards and their "
                    "most important settings. To view all "
                    f"settings, run `{p}starboards #starboard`."
                ),
                color=self.bot.theme_color,
            )
            for s in starboards:
                c = ctx.guild.get_channel(s["id"])
                emoji_str = utils.pretty_emoji_string(
                    s["star_emojis"], ctx.guild
                )
                embed.add_field(
                    name=c.name if c else f"Deleted Channel {s['id']}",
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
            embed = discord.Embed(
                title=starboard.obj.name,
                description=(
                    f"emojis: **{upvote_emoji_str}**\n"
                    f"displayEmoji: **{s['display_emoji']}**\n"
                    f"color: **{s['color']}**\n\n"
                    f"requiredStars: **{s['required']}**\n"
                    f"requiredRemove: **{s['required_remove']}**\n"
                    f"selfStar: **{s['self_star']}**\n"
                    f"allowBots: **{s['allow_bots']}**\n"
                    f"imagesOnly: **{s['images_only']}**\n"
                    f"regex: `{s['regex'] or 'None'}`\n"
                    f"excludeRegex: `{s['exclude_regex'] or 'None'}`\n\n"
                    f"ping: **{s['ping']}**\n"
                    f"autoReact: **{s['autoreact']}**\n"
                    f"linkDeletes: **{s['link_deletes']}**\n"
                    f"linkEdits: **{s['link_edits']}**\n"
                    f"noXp: **{s['no_xp']}**\n"
                    f"allowRandom: **{s['explore']}**\n"
                ),
                color=self.bot.theme_color,
            )
            await ctx.send(embed=embed)

    @starboards.command(name="add", aliases=["a"], brief="Adds a starboard")
    @commands.has_guild_permissions(manage_channels=True)
    async def add_starboard(
        self, ctx: commands.Context, channel: discord.TextChannel
    ) -> None:
        """Adds a starboard"""
        existed = await self.bot.db.starboards.create(channel.id, ctx.guild.id)
        if existed:
            raise errors.AlreadyExists(
                f"{channel.mention} is already a starboard."
            )
        else:
            await ctx.send(f"Created starboard {channel.mention}")

    @starboards.command(
        name="remove",
        aliases=["delete", "del", "r"],
        brief="Removes a starboard",
    )
    @commands.has_guild_permissions(manage_channels=True)
    async def remove_starboard(
        self, ctx: commands.Context, channel: Union[discord.TextChannel, int]
    ) -> None:
        """Deletes a starboard. Will not actually
        delete the channel, or the messages in the
        channel. This action is irreversable."""
        cid = channel.id if type(channel) is not int else channel
        cname = channel.mention if type(channel) is not int else channel
        starboard = await self.bot.db.starboards.get(cid)
        if not starboard:
            raise errors.DoesNotExist(f"{cname} is not a starboard.")
        else:
            await ctx.send(
                "Are you sure? All starboard messages will be lost."
            )
            confirmed = await utils.confirm(ctx)
            if confirmed is True:
                await self.bot.db.starboards.delete(cid)
                await ctx.send(f"{cname} is no longer a starboard.")
            if confirmed is False:
                await ctx.send("Cancelled.")

    @starboards.command(
        name="displayEmoji",
        aliases=["de"],
        brief="Set the emoji to show next to the points",
    )
    @commands.has_guild_permissions(manage_channels=True)
    async def set_display_emoji(
        self,
        ctx: commands.Context,
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
        brief="Sets the embed color of starboard messages",
    )
    @commands.has_guild_permissions(manage_channels=True)
    async def set_color(
        self,
        ctx: commands.Context,
        starboard: converters.Starboard,
        color: converters.myhex,
    ) -> None:
        await self.bot.db.starboards.edit(starboard.obj.id, color=color)
        await ctx.send(
            embed=utils.cs_embed(
                {"color": (starboard.sql["color"], color)}, self.bot
            )
        )

    @starboards.command(
        name="required",
        aliases=["requiredStars", "requiredPoints"],
        brief="Sets the number of reactions a message needs",
    )
    @commands.has_guild_permissions(manage_channels=True)
    async def set_required(
        self,
        ctx: commands.Context,
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
        brief="How few stars a message has before it is removed",
    )
    @commands.has_guild_permissions(manage_channels=True)
    async def set_required_remove(
        self,
        ctx: commands.Context,
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
        brief="Whether or not users can star their own messages",
    )
    @commands.has_guild_permissions(manage_channels=True)
    async def set_self_star(
        self,
        ctx: commands.Context,
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
        brief="Whether or not bot messages can appear on the starboard",
    )
    @commands.has_guild_permissions(manage_channels=True)
    async def set_allow_Bots(
        self,
        ctx: commands.Context,
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
        brief="Whether messages must include an image",
    )
    @commands.has_guild_permissions(manage_channels=True)
    async def set_images_only(
        self,
        ctx: commands.Context,
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
        brief="A regex string that all messages must match",
    )
    @commands.has_guild_permissions(manage_channels=True)
    async def set_regex(
        self,
        ctx: commands.Context,
        starboard: converters.Starboard,
        regex: str,
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
        brief="A regex string that all messages must not match",
    )
    @commands.has_guild_permissions(manage_channels=True)
    async def set_eregex(
        self,
        ctx: commands.context,
        starboard: converters.Starboard,
        exclude_regex: str,
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
        brief="Whether or not to mention the author of a starboard message",
    )
    @commands.has_guild_permissions(manage_channels=True)
    async def set_ping(
        self,
        ctx: commands.Context,
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
        brief="Whether to automatically react to starboard messages",
    )
    @commands.has_guild_permissions(manage_channels=True)
    async def set_auto_react(
        self,
        ctx: commands.Context,
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
        brief="Whether to delete the starboard message if the original is",
    )
    @commands.has_guild_permissions(manage_channels=True)
    async def set_link_deletes(
        self,
        ctx: commands.Context,
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
        brief="Whether to update starboard messages with edited content",
    )
    @commands.has_guild_permissions(manage_channels=True)
    async def set_link_edits(
        self,
        ctx: commands.Context,
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
        brief="Set to True to disable gaining XP for this starboard",
    )
    @commands.has_guild_permissions(manage_channels=True)
    async def set_no_xp(
        self,
        ctx: commands.Context,
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
        name="allowRandom",
        aliases=["rand", "explore"],
        brief="Whether or not the random command can pull from this starboard",
    )
    @commands.has_guild_permissions(manage_channels=True)
    async def set_allow_random(
        self,
        ctx: commands.Context,
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
        brief="Modify starEmojis for a starboard",
        invoke_without_command=True,
    )
    @commands.has_guild_permissions(manage_guild=True)
    async def star_emojis(self, ctx: commands.Context) -> None:
        """Modify the star emojis for a starboard"""
        await ctx.send(
            "Options:\n "
            "- `starEmojis add <starboard> <emoji>`\n"
            " - `starEmojis remove <starboard> <emoji>`\n"
            " - `starEmojis clear <starboard>`"
        )

    @star_emojis.command(name="add", aliases=["a"], brief="Add a starEmoji")
    @commands.has_guild_permissions(manage_guild=True)
    async def add_star_emoji(
        self,
        ctx: commands.Context,
        starboard: converters.Starboard,
        emoji: converters.Emoji,
    ) -> None:
        """Adds a starEmoji to a starboard"""
        converted_emoji = utils.clean_emoji(emoji)

        current_emojis = starboard.sql["star_emojis"]

        if converted_emoji in current_emojis:
            raise errors.AlreadyExists(
                f"{emoji} is already a starEmoji on "
                f"{starboard.obj.mention}"
            )

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
        name="remove", aliases=["r", "del"], brief="Removes a starEmoji"
    )
    @commands.has_guild_permissions(manage_channels=True)
    async def remove_star_emoji(
        self,
        ctx: commands.Context,
        starboard: converters.Starboard,
        emoji: converters.Emoji,
    ) -> None:
        """Removes a starEmoji from a starboard"""
        converted_emoji = utils.clean_emoji(emoji)

        current_emojis = starboard.sql["star_emojis"]

        if converted_emoji not in current_emojis:
            raise errors.DoesNotExist(
                f"{emoji} is not a starEmoji on " f"{starboard.obj.mention}"
            )

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
        brief="Clears all starEmojis for a starboard",
    )
    @commands.has_guild_permissions(manage_channels=True)
    async def clear_star_emojis(
        self, ctx: commands.Context, starboard: converters.Starboard
    ) -> None:
        """Removes all starEmojis from a starboard"""
        await ctx.send("Are you sure?")
        if not await utils.confirm(ctx):
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
