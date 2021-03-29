import discord
from discord.ext import commands, flags

from app import converters, errors, utils, menus
from app.classes.bot import Bot
from app.cogs.starboard import starboard_funcs

from . import cleaner, debugger, recounter, utility_funcs


class Utility(commands.Cog):
    "Utility and starboard moderation"

    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.command(
        name="scan", brief="Recounts the reactions on lots of messages at once"
    )
    @commands.max_concurrency(1, per=commands.BucketType.guild)
    @commands.has_guild_permissions(manage_guild=True)
    @commands.bot_has_permissions(read_message_history=True)
    @commands.guild_only()
    async def scan_recount(self, ctx: commands.Context, limit: int) -> None:
        if limit < 1:
            await ctx.send("Must recount at least 1 message.")
            return
        if limit > 1000:
            await ctx.send("Can only recount up to 1,000 messages.")
            return
        async with ctx.typing():
            await recounter.scan_recount(self.bot, ctx.channel, limit)
        await ctx.send("Finished!")

    @commands.command(
        name="recount",
        aliases=["refresh"],
        brief="Recounts the reactions on a message",
    )
    @commands.cooldown(3, 6, type=commands.BucketType.guild)
    @commands.has_guild_permissions(manage_messages=True)
    async def recount(
        self, ctx: commands.Context, message: converters.MessageLink
    ) -> None:
        orig_sql_message = await starboard_funcs.orig_message(
            self.bot, message.id
        )
        if not orig_sql_message:
            await self.bot.db.messages.create(
                message.id,
                ctx.guild.id,
                ctx.channel.id,
                ctx.author.id,
                ctx.channel.is_nsfw(),
            )
        else:
            message = await self.bot.cache.fetch_message(
                ctx.guild.id,
                int(orig_sql_message["channel_id"]),
                int(orig_sql_message["id"]),
            )
        async with ctx.typing():
            await recounter.recount_reactions(self.bot, message)
        await ctx.send("Finished!")

    @commands.command(
        name="clean",
        brief="Cleans things like #deleted-channel and @deleted-role",
    )
    @commands.cooldown(1, 5, type=commands.BucketType.guild)
    @commands.has_guild_permissions(manage_guild=True)
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def clean(self, ctx: commands.Context) -> None:
        result = await cleaner.clean_guild(ctx.guild, self.bot)
        string = "\n".join(
            f"{name}: {count}" for name, count in result if count != 0
        )
        if string == "":
            string = "Nothing to remove"
        embed = discord.Embed(
            title="Database Cleaning",
            description=string,
            color=self.bot.theme_color,
        )
        await ctx.send(embed=embed)

    @commands.command(
        name="debug", brief="Looks for problems with your current setup"
    )
    @commands.cooldown(2, 5, type=commands.BucketType.guild)
    @commands.has_guild_permissions(manage_guild=True)
    @commands.bot_has_permissions(
        embed_links=True, add_reactions=True, read_message_history=True
    )
    @commands.guild_only()
    async def debug(self, ctx: commands.Context) -> None:
        result = await debugger.debug_guild(self.bot, ctx.guild)

        p = commands.Paginator(prefix="", suffix="")

        p.add_line(
            f"{len(result['errors'])} errors, "
            f"{len(result['warns'])} warnings, "
            f"{len(result['light_warns'])} notes, "
            f"and {len(result['suggestions'])} suggestions."
        )
        if result["errors"]:
            p.add_line("\n\n**Errors:**")
            for e in result["errors"]:
                p.add_line(f"\n{e}")
        if result["warns"]:
            p.add_line("\n\n**Warnings:**")
            for e in result["warns"]:
                p.add_line(f"\n{e}")
        if result["light_warns"]:
            p.add_line("\n\n**Notes:**")
            for e in result["light_warns"]:
                p.add_line(f"\n{e}")
        if result["suggestions"]:
            p.add_line("\n\n**Suggestions:**")
            for e in result["suggestions"]:
                p.add_line(f"\n{e}")

        embeds = [
            discord.Embed(
                title="Debugging Results",
                description=page,
                color=self.bot.theme_color,
            )
            for page in p.pages
        ]
        await menus.Paginator(embeds=embeds, delete_after=True).start(ctx)

    @commands.command(name="freeze", brief="Freeze a message")
    @commands.has_guild_permissions(manage_messages=True)
    async def freeze_message(
        self, ctx: commands.Context, message_link: converters.MessageLink
    ) -> None:
        """Freezes a message, so the point count will
        not update."""
        orig_message = await starboard_funcs.orig_message(
            self.bot, message_link.id
        )
        if not orig_message:
            raise errors.DoesNotExist(
                "I couldn't freeze the message because "
                "it does not exist in the database."
            )
        await utility_funcs.handle_freezing(
            self.bot, orig_message["id"], orig_message["guild_id"], True
        )
        await ctx.send("Message frozen")

    @commands.command(name="unfreeze", brief="Unfreezes a message")
    @commands.has_guild_permissions(manage_messages=True)
    async def unfreeze_message(
        self, ctx: commands.Context, message_link: converters.MessageLink
    ) -> None:
        """Unfreezes a message"""
        orig_message = await starboard_funcs.orig_message(
            self.bot, message_link.id
        )
        if not orig_message:
            raise errors.DoesNotExist(
                "I can't unfreeze that messsage because "
                "it does not exist in the database."
            )
        await utility_funcs.handle_freezing(
            self.bot, orig_message["id"], orig_message["guild_id"], False
        )
        await ctx.send("Message unfrozen")

    @commands.command(
        name="force", brief="Forced a message to certain starboards"
    )
    @commands.has_guild_permissions(manage_messages=True)
    @commands.bot_has_permissions(
        add_reactions=True, read_message_history=True
    )
    @commands.guild_only()
    async def force_message(
        self,
        ctx: commands.Context,
        message_link: converters.MessageLink,
        *starboards: converters.Starboard,
    ) -> None:
        """Forces a message to all or some starboards.

        A forced message will appear on the starboard,
        event if the channel is blacklisted, the
        message author is blacklisted, or the number of
        reaction on the message is less than the starboards
        required setting.

        Usage:
            force <message link> [starboard1, starboard2, ...]
        Examples:
            force <message link> #starboard #super-starboard
            force <message link> #super-starboard
            force <message link>
        """
        starboards = [int(s.sql["id"]) for s in starboards]
        if len(starboards) == 0:
            if not await menus.Confirm(
                "Force this message to all starboards?"
            ).start(ctx):
                await ctx.send("Cancelled")
                return
        orig_sql_message = await starboard_funcs.orig_message(
            self.bot, message_link.id
        )
        if orig_sql_message is None:
            await self.bot.db.users.create(
                message_link.author.id, message_link.author.bot
            )
            await self.bot.db.messages.create(
                message_link.id,
                message_link.guild.id,
                message_link.channel.id,
                message_link.author.id,
                message_link.channel.is_nsfw(),
            )
            orig_sql_message = await self.bot.db.messages.get(message_link.id)

        await utility_funcs.handle_forcing(
            self.bot,
            orig_sql_message["id"],
            orig_sql_message["guild_id"],
            starboards,
            True,
        )
        if len(starboards) == 0:
            await ctx.send("Message forced to all starboards")
        else:
            converted = [f"<#{s}>" for s in starboards]
            await ctx.send(f"Message forced to {', '.join(converted)}")

    @commands.command(
        name="unforce", brief="Unforces a message from certain starboards"
    )
    @commands.has_guild_permissions(manage_messages=True)
    @commands.bot_has_permissions(
        add_reactions=True, read_message_history=True
    )
    @commands.guild_only()
    async def unforce_message(
        self,
        ctx: commands.Context,
        message_link: converters.MessageLink,
        *starboards: converters.Starboard,
    ) -> None:
        """Unforces a message

        Usage:
            unforce <message link> [starboard1, starboard2, ...]
        Examples:
            unforce <message link> #starboard #super-starboard
            unforce <message link> #super-starboard
            unforce <message link>"""
        starboards = [int(s.sql["id"]) for s in starboards]

        orig_sql_message = await starboard_funcs.orig_message(
            self.bot, message_link.id
        )
        if not orig_sql_message:
            await ctx.send("That message does not exist in the database")
        if orig_sql_message["id"] != message_link.id and len(starboards) == 0:
            if await menus.Confirm(
                "The message you passed appears to be a starboard "
                "message. Would you like to unforce this message "
                f"from {message_link.channel.mention} instead?"
            ).start(ctx):
                starboards = [message_link.channel.id]

        if len(starboards) == 0:
            if not await menus.Confirm(
                "Unforce this message from all starboards?"
            ).start(ctx):
                await ctx.send("Cancelled")
                return
        await utility_funcs.handle_forcing(
            self.bot,
            orig_sql_message["id"],
            orig_sql_message["guild_id"],
            starboards,
            False,
        )
        if len(starboards) == 0:
            await ctx.send("Message unforced from all starboards")
        else:
            converted = [f"<#{s}>" for s in starboards]
            await ctx.send(f"Message unforced from {', '.join(converted)}")

    @commands.command(
        name="trashreason",
        aliases=["reason"],
        brief="Sets the reason for trashing a message",
    )
    @commands.has_guild_permissions(manage_messages=True)
    async def set_trash_reason(
        self,
        ctx: commands.Context,
        message: converters.MessageLink,
        *,
        reason: str = None,
    ) -> None:
        orig_message = await starboard_funcs.orig_message(self.bot, message.id)
        if not orig_message:
            raise errors.DoesNotExist(
                "That message does not exist in the database."
            )
        await utility_funcs.set_trash_reason(
            self.bot, orig_message["id"], ctx.guild.id, reason or "None given"
        )
        await ctx.send(f"Set the reason to {reason}")

    @commands.command(
        name="trash", brief="Trashes a message so it can't be viewed"
    )
    @commands.has_guild_permissions(manage_messages=True)
    async def trash_message(
        self,
        ctx: commands.Context,
        message_link: converters.MessageLink,
        *,
        reason=None,
    ) -> None:
        """Trashes a message for all starboards.

        A trashed message cannot be starred, added to
        more starboards, or be viewed on any of the
        current starboards."""
        orig_sql_message = await starboard_funcs.orig_message(
            self.bot, message_link.id
        )
        if not orig_sql_message:
            raise errors.DoesNotExist(
                "That message has not been starred, so I " "can't trash it."
            )
        await utility_funcs.handle_trashing(
            self.bot,
            orig_sql_message["id"],
            orig_sql_message["guild_id"],
            True,
            reason or "No reason given",
        )
        await ctx.send("Message trashed")

    @commands.command(name="untrash", brief="Untrashes a message")
    @commands.has_guild_permissions(manage_messages=True)
    async def untrash_message(
        self, ctx: commands.Context, message_link: converters.MessageLink
    ) -> None:
        """Untrashes a message for all starboards"""
        orig_sql_message = await starboard_funcs.orig_message(
            self.bot, message_link.id
        )
        if not orig_sql_message:
            raise errors.DoesNotExist(
                "That message does not exist in the database."
            )
        await utility_funcs.handle_trashing(
            self.bot,
            orig_sql_message["id"],
            orig_sql_message["guild_id"],
            False,
        )
        await ctx.send("Message untrashed")

    @commands.command(
        name="trashcan",
        aliases=["trashed"],
        brief="Shows a list of trashed messages",
    )
    @commands.has_guild_permissions(manage_messages=True)
    @commands.bot_has_permissions(
        embed_links=True, add_reactions=True, read_message_history=True
    )
    @commands.guild_only()
    async def show_trashcan(self, ctx: commands.Context) -> None:
        """Shows all messages that have been trashed."""
        trashed_messages = await self.bot.db.fetch(
            """SELECT * FROM messages
            WHERE guild_id=$1 AND trashed=True""",
            ctx.guild.id,
        )
        if len(trashed_messages) == 0:
            await ctx.send("You have no trashed messages.")
            return
        p = commands.Paginator(prefix="", suffix="", max_size=2000)
        for m in trashed_messages:
            link = utils.jump_link(m["id"], m["channel_id"], m["guild_id"])
            p.add_line(
                f"**[{m['channel_id']}-{m['id']}]({link})**: "
                f"`{utils.escmd(m['trash_reason'])}`"
            )
        embeds = [
            discord.Embed(
                title="Trashed Messages",
                description=page,
                color=self.bot.theme_color,
            )
            for page in p.pages
        ]
        await menus.Paginator(embeds=embeds).start(ctx)

    @flags.add_flag("--by", type=discord.User)
    @flags.add_flag("--notby", type=discord.User)
    @flags.add_flag("--contains", type=str)
    @flags.command(
        name="purge", brief="Trashes a large number of messages at once"
    )
    @commands.has_guild_permissions(manage_messages=True)
    @commands.bot_has_permissions(read_message_history=True, embed_links=True)
    @commands.guild_only()
    async def purgetrash(
        self, ctx: commands.Context, limit: converters.myint, **flags
    ) -> None:
        """Works similar to a normal purge command,
        but instead of deleting the messages, each
        message is trashed. See sb!help trash for
        info on trashing.

        Can only trash up to 200 messages at once.

        Usage:
            purge <limit> <options>
        Options:
            --by: Only trash messages by this author
            --notby: Do not trash message by this author
            --contains: Only trash messages that contain
                this phrase.
        Examples:
            trash 50 --by @Circuit
            trash 50 --contains bad-word
            trash 50 --notby @Cool Person
            trash 50"""
        if limit > 200:
            raise discord.InvalidArgument(
                "Can only purge up to 200 messages at once"
            )
        elif limit < 1:
            raise discord.InvalidArgument("Must purge at least 1 message")

        total, purged = await utility_funcs.handle_purging(
            self.bot,
            ctx.channel,
            limit,
            True,
            flags["by"],
            flags["notby"],
            flags["contains"],
        )

        embed = discord.Embed(
            title=f"Purged {total} Messages",
            description="\n".join([f"<@{u}>: {c}" for u, c in purged.items()]),
            color=self.bot.theme_color,
        )

        await ctx.send(embed=embed)

    @flags.add_flag("--by", type=discord.User)
    @flags.add_flag("--notby", type=discord.User)
    @flags.add_flag("--contains", type=str)
    @flags.command(
        name="unpurge", brief="Untrashes a large number of messages at once"
    )
    @commands.has_guild_permissions(manage_messages=True)
    @commands.bot_has_permissions(read_message_history=True, embed_links=True)
    async def unpurgetrash(
        self, ctx: commands.Context, limit: converters.myint, **flags
    ) -> None:
        """Same usage as purge, but untrashes instead."""
        if limit > 200:
            raise discord.InvalidArgument(
                "Can only unpurge up to 200 messages at once"
            )
        elif limit < 1:
            raise discord.InvalidArgument("Must unpurge at least 1 message")

        total, purged = await utility_funcs.handle_purging(
            self.bot,
            ctx.channel,
            limit,
            False,
            flags["by"],
            flags["notby"],
            flags["contains"],
        )

        embed = discord.Embed(
            title=f"Unpurged {total} Messages",
            description="\n".join([f"<@{u}>: {c}" for u, c in purged.items()]),
            color=self.bot.theme_color,
        )

        await ctx.send(embed=embed)

    @commands.command(
        name="messageInfo",
        aliases=["mi"],
        brief="Shows information on a message",
    )
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def message_info(
        self, ctx: commands.Context, message: converters.MessageLink
    ) -> None:
        """Shows useful info on a message."""
        orig = await starboard_funcs.orig_message(self.bot, message.id)
        if not orig:
            raise errors.DoesNotExist(
                "That message does not exist in the database."
            )
        jump = utils.jump_link(
            orig["id"], orig["channel_id"], orig["guild_id"]
        )
        embed = discord.Embed(
            title="Message Info",
            color=self.bot.theme_color,
            description=(
                f"[Jump to Message]({jump})\n"
                f"Channel: <#{orig['channel_id']}>\n"
                f"ID: {orig['id']} (`{orig['channel_id']}-{orig['id']}`)\n"
                f"Author: <@{orig['author_id']}> | `{orig['author_id']}`\n"
                f"Trashed: {orig['trashed']}\n"
                f"Frozen: {orig['frozen']}"
            ),
        )
        for s in await self.bot.db.starboards.get_many(ctx.guild.id):
            s_obj = ctx.guild.get_channel(int(s["id"]))
            if not s_obj:
                continue
            sb_message = await self.bot.db.fetchrow(
                """SELECT * FROM starboard_messages
                WHERE orig_id=$1 AND starboard_id=$2""",
                orig["id"],
                s["id"],
            )
            if not sb_message:
                jump = "Not On Starboard"
                points = 0
                forced = False
            else:
                _jump = utils.jump_link(
                    sb_message["id"],
                    sb_message["starboard_id"],
                    orig["guild_id"],
                )
                jump = f"[Jump]({_jump})"
                points = sb_message["points"]
                forced = s["id"] in orig["forced"]
            embed.add_field(
                name=s_obj.name,
                value=(
                    f"<#{s['id']}>: {jump}\nPoints: "
                    f"**{points}**/{s['required']}\nForced: {forced}"
                ),
            )

        await ctx.send(embed=embed)


def setup(bot: Bot) -> None:
    bot.add_cog(Utility(bot))
