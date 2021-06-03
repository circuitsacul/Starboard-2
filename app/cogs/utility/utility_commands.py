import asyncio

import discord
from discord.ext.prettyhelp import bot_has_permissions, has_guild_permissions

from app import buttons, checks, commands, converters, errors, flags, utils
from app.classes.bot import Bot
from app.classes.context import MyContext
from app.cogs.leveling import leveling_funcs
from app.cogs.starboard import starboard_funcs
from app.i18n import t_

from . import cleaner, debugger, recounter, utility_funcs


class Utility(
    commands.Cog, description=t_("Utility and moderation commands.", True)
):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.command(
        name="cleanup",
        help=t_(
            "Removes command invocations and their responses for this bot.",
            True,
        ),
    )
    @has_guild_permissions(manage_messages=True)
    @bot_has_permissions(read_message_history=True, manage_messages=True)
    @commands.guild_only()
    async def cleanup(self, ctx: "MyContext"):
        to_cleanup = self.bot.to_cleanup[ctx.guild.id]._values

        def check(m: discord.Message) -> bool:
            if m.id in to_cleanup:
                return True
            return False

        await ctx.channel.purge(check=check, limit=200)

        await ctx.message.delete()
        await ctx.send("Done", delete_after=3)

    @commands.group(
        name="reset",
        help=t_("A utility for resetting aspects of the bot.", True),
        invoke_without_command=True,
    )
    @has_guild_permissions(administrator=True)
    @commands.guild_only()
    async def reset(self, ctx: "MyContext"):
        await ctx.send_help(ctx.command)

    @reset.command(name="all", help=t_("Resets the bot for your guild.", True))
    @has_guild_permissions(administrator=True)
    @commands.guild_only()
    async def reset_all(self, ctx: "MyContext"):
        await ctx.send(
            t_(
                "You are about to reset all settings, starboards, "
                "autostarchannels, and leaderboard data for this "
                "server. Please type the name of this server to "
                "continue, or anything else to cancel."
            )
        )

        def check(m: discord.Message) -> bool:
            if m.author.id != ctx.author.id:
                return False
            if m.channel.id != ctx.channel.id:
                return False
            return True

        try:
            m = await self.bot.wait_for("message", check=check)
        except asyncio.TimeoutError:
            await ctx.send(t_("Cancelled."))
            return
        if m.content.casefold() != ctx.guild.name.casefold():
            await ctx.send(t_("Cancelled."))
            return

        if not await buttons.Confirm(ctx, t_("Are you certain?")).start():
            await ctx.send(t_("Cancelled."))
            return

        await self.bot.db.guilds.delete(ctx.guild.id)
        await ctx.send(t_("Starboard has been reset for this server."))

    @reset.command(
        name="leaderboard",
        aliases=["lb"],
        help=t_("Resets the leaderboard.", True),
    )
    @has_guild_permissions(manage_guild=True)
    @commands.guild_only()
    async def reset_lb(self, ctx: "MyContext"):
        if not await buttons.Confirm(
            ctx, t_("Reset the leaderboard?")
        ).start():
            await ctx.send(t_("Cancelled."))
            return
        await self.bot.db.execute(
            """UPDATE members
            SET xp=0,
            level=0
            WHERE guild_id=$1""",
            ctx.guild.id,
        )
        await ctx.send(t_("Reset the leaderboard."))

    @commands.command(name="setxp", help=t_("Sets the XP for a user.", True))
    @has_guild_permissions(manage_guild=True)
    async def set_user_xp(
        self, ctx: "MyContext", user: discord.User, xp: converters.myint
    ):
        if xp < 0:
            raise commands.BadArgument(t_("XP cannot be less than 0."))
        if xp > 2_147_483_647:
            raise commands.BadArgument(
                t_("XP cannot be greater than 2,147,483,647.")
            )

        sql_member = await self.bot.db.members.get(user.id, ctx.guild.id)
        if not sql_member:
            raise commands.BadArgument(
                t_("That user does not exist in the database for this guild.")
            )

        new_level = leveling_funcs.current_level(xp)
        await self.bot.db.execute(
            """UPDATE members
            SET xp=$1,
            level=$2
            WHERE user_id=$3
            AND guild_id=$4""",
            xp,
            new_level,
            user.id,
            ctx.guild.id,
        )

        await ctx.send(
            t_(
                "Changed {0}'s XP to {1} and Level to {2} "
                "(was {3} XP and Level {4})."
            ).format(
                user.name, xp, new_level, sql_member["xp"], sql_member["level"]
            )
        )

    @commands.command(
        name="scan",
        help=t_("Recounts the reactions on lots of messages at once.", True),
    )
    @commands.max_concurrency(1, per=commands.BucketType.guild)
    @has_guild_permissions(manage_guild=True)
    @bot_has_permissions(read_message_history=True)
    @commands.guild_only()
    @checks.premium_guild()
    async def scan_recount(
        self, ctx: "MyContext", limit: converters.myint
    ) -> None:
        if limit < 1:
            await ctx.send(t_("Must recount at least 1 message."))
            return
        if limit > 1000:
            await ctx.send(t_("Can only recount up to 1,000 messages."))
            return
        async with ctx.typing():
            await recounter.scan_recount(self.bot, ctx.channel, limit)
        await ctx.send("Finished!")

    @commands.command(
        name="recount",
        aliases=["refresh"],
        help=t_("Recounts the reactions on a message.", True),
    )
    @commands.cooldown(3, 6, type=commands.BucketType.guild)
    @has_guild_permissions(manage_messages=True)
    async def recount(
        self, ctx: "MyContext", message: converters.GuildMessage
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
        help=t_(
            "Cleans things like #deleted-channel and @deleted-role.\n"
            "Note that this can change the functionality of things "
            "such as PermRoles and channel blacklists/whitelists.",
            True,
        ),
    )
    @commands.cooldown(1, 5, type=commands.BucketType.guild)
    @has_guild_permissions(manage_guild=True)
    @bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def clean(self, ctx: "MyContext") -> None:
        result = await cleaner.clean_guild(ctx.guild, self.bot)
        string = "\n".join(
            f"{name}: {count}" for name, count in result if count != 0
        )
        if string == "":
            string = t_("Nothing to remove")
        embed = discord.Embed(
            title=t_("Database Cleaning"),
            description=string,
            color=self.bot.theme_color,
        )
        await ctx.send(embed=embed)

    @commands.command(
        name="debug",
        help=t_("Looks for problems with your current setup.", True),
    )
    @commands.cooldown(2, 5, type=commands.BucketType.guild)
    @has_guild_permissions(manage_guild=True)
    @bot_has_permissions(
        embed_links=True, add_reactions=True, read_message_history=True
    )
    @commands.guild_only()
    async def debug(self, ctx: "MyContext") -> None:
        result = await debugger.debug_guild(self.bot, ctx.guild)

        p = commands.Paginator(prefix="", suffix="")

        p.add_line(
            t_(
                "{0} errors, {1} warnings, {2} notes, and {3} suggestions."
            ).format(
                len(result["errors"]),
                len(result["warns"]),
                len(result["light_warns"]),
                len(result["suggestions"]),
            )
        )
        if result["errors"]:
            p.add_line(t_("\n\n**Errors:**"))
            for e in result["errors"]:
                p.add_line(f"\n{e}")
        if result["warns"]:
            p.add_line(t_("\n\n**Warnings:**"))
            for e in result["warns"]:
                p.add_line(f"\n{e}")
        if result["light_warns"]:
            p.add_line(t_("\n\n**Notes:**"))
            for e in result["light_warns"]:
                p.add_line(f"\n{e}")
        if result["suggestions"]:
            p.add_line(t_("\n\n**Suggestions:**"))
            for e in result["suggestions"]:
                p.add_line(f"\n{e}")

        embeds = [
            discord.Embed(
                title=t_("Debugging Results"),
                description=page,
                color=self.bot.theme_color,
            )
            for page in p.pages
        ]
        await buttons.Paginator(
            ctx,
            embed_pages=embeds,
            delete_after=True,
        ).start()

    @commands.command(name="freeze", help=t_("Freezes a message.", True))
    @has_guild_permissions(manage_messages=True)
    async def freeze_message(
        self, ctx: "MyContext", message: converters.PartialGuildMessage
    ) -> None:
        orig_message = await starboard_funcs.orig_message(self.bot, message.id)
        if not orig_message:
            raise errors.MessageNotInDatabse()
        await utility_funcs.handle_freezing(
            self.bot, orig_message["id"], orig_message["guild_id"], True
        )
        await ctx.send("Message frozen.")

    @commands.command(name="unfreeze", help=t_("Unfreezes a message.", True))
    @has_guild_permissions(manage_messages=True)
    async def unfreeze_message(
        self, ctx: "MyContext", message: converters.PartialGuildMessage
    ) -> None:
        orig_message = await starboard_funcs.orig_message(self.bot, message.id)
        if not orig_message:
            raise errors.MessageNotInDatabse()
        await utility_funcs.handle_freezing(
            self.bot, orig_message["id"], orig_message["guild_id"], False
        )
        await ctx.send(t_("Message unfrozen."))

    @commands.command(
        name="force", help=t_("Force a message to certain starboards.", True)
    )
    @has_guild_permissions(manage_messages=True)
    @bot_has_permissions(add_reactions=True, read_message_history=True)
    @commands.guild_only()
    async def force_message(
        self,
        ctx: "MyContext",
        message: converters.GuildMessage,
        *starboards: converters.Starboard,
    ) -> None:
        starboards = [int(s.sql["id"]) for s in starboards]
        if len(starboards) == 0:
            if not await buttons.Confirm(
                ctx, t_("Force this message to all starboards?")
            ).start():
                await ctx.send(t_("Cancelled."))
                return
        orig_sql_message = await starboard_funcs.orig_message(
            self.bot, message.id
        )
        if orig_sql_message is None:
            await self.bot.db.users.create(
                message.author.id, message.author.bot
            )
            await self.bot.db.messages.create(
                message.id,
                message.guild.id,
                message.channel.id,
                message.author.id,
                message.channel.is_nsfw(),
            )
            orig_sql_message = await self.bot.db.messages.get(message.id)

        await utility_funcs.handle_forcing(
            self.bot,
            orig_sql_message["id"],
            orig_sql_message["guild_id"],
            starboards,
            True,
        )
        if len(starboards) == 0:
            await ctx.send(t_("Message forced to all starboards."))
        else:
            converted = [f"<#{s}>" for s in starboards]
            await ctx.send(
                t_("Message forced to {0}.").format(", ".join(converted))
            )

    @commands.command(
        name="unforce",
        help=t_("Unforces a message from certain starboards.", True),
    )
    @has_guild_permissions(manage_messages=True)
    @bot_has_permissions(add_reactions=True, read_message_history=True)
    @commands.guild_only()
    async def unforce_message(
        self,
        ctx: "MyContext",
        message_link: converters.GuildMessage,
        *starboards: converters.Starboard,
    ) -> None:
        starboards = [int(s.sql["id"]) for s in starboards]

        orig_sql_message = await starboard_funcs.orig_message(
            self.bot, message_link.id
        )
        if not orig_sql_message:
            raise errors.MessageNotInDatabse()
        if orig_sql_message["id"] != message_link.id and len(starboards) == 0:
            if await buttons.Confirm(
                ctx,
                t_(
                    "The message you passed appears to be a starboard "
                    "message. Would you like to unforce this message "
                    "from {0} instead?"
                ).format(message_link.channel.mention),
            ).start():
                starboards = [message_link.channel.id]

        if len(starboards) == 0:
            if not await buttons.Confirm(
                ctx, t_("Unforce this message from all starboards?")
            ).start():
                await ctx.send(t_("Cancelled."))
                return
        await utility_funcs.handle_forcing(
            self.bot,
            orig_sql_message["id"],
            orig_sql_message["guild_id"],
            starboards,
            False,
        )
        if len(starboards) == 0:
            await ctx.send(t_("Message unforced from all starboards."))
        else:
            converted = [f"<#{s}>" for s in starboards]
            await ctx.send(
                t_("Message unforced from {0}.").format(", ".join(converted))
            )

    @commands.command(
        name="trashreason",
        aliases=["reason"],
        help=t_("Sets the reason for trashing a message.", True),
    )
    @has_guild_permissions(manage_messages=True)
    async def set_trash_reason(
        self,
        ctx: "MyContext",
        message: converters.GuildMessage,
        *,
        reason: str = None,
    ) -> None:
        orig_message = await starboard_funcs.orig_message(self.bot, message.id)
        if not orig_message:
            raise errors.MessageNotInDatabse()
        await utility_funcs.set_trash_reason(
            self.bot, orig_message["id"], ctx.guild.id, reason or "None given"
        )
        await ctx.send(t_("Set the reason to {0}.").format(reason))

    @commands.command(
        name="trash", help=t_("Trashes a message so it can't be viewed.", True)
    )
    @has_guild_permissions(manage_messages=True)
    async def trash_message(
        self,
        ctx: "MyContext",
        message_link: converters.GuildMessage,
        *,
        reason=None,
    ) -> None:
        orig_sql_message = await starboard_funcs.orig_message(
            self.bot, message_link.id
        )
        if not orig_sql_message:
            raise errors.MessageNotInDatabse()
        await utility_funcs.handle_trashing(
            self.bot,
            orig_sql_message["id"],
            orig_sql_message["guild_id"],
            True,
            reason or "No reason given",
        )
        await ctx.send(t_("Message trashed."))

    @commands.command(name="untrash", help=t_("Untrashes a message.", True))
    @has_guild_permissions(manage_messages=True)
    async def untrash_message(
        self,
        ctx: "MyContext",
        message_link: converters.PartialGuildMessage,
    ) -> None:
        orig_sql_message = await starboard_funcs.orig_message(
            self.bot, message_link.id
        )
        if not orig_sql_message:
            raise errors.MessageNotInDatabse()
        await utility_funcs.handle_trashing(
            self.bot,
            orig_sql_message["id"],
            orig_sql_message["guild_id"],
            False,
        )
        await ctx.send(t_("Message untrashed."))

    @commands.group(
        name="trashcan",
        aliases=["trashed"],
        help=t_("Shows a list of trashed messages.", True),
        invoke_without_command=True,
    )
    @has_guild_permissions(manage_messages=True)
    @bot_has_permissions(
        embed_links=True, add_reactions=True, read_message_history=True
    )
    @commands.guild_only()
    async def trashcan(self, ctx: "MyContext") -> None:
        trashed_messages = await self.bot.db.fetch(
            """SELECT * FROM messages
            WHERE guild_id=$1 AND trashed=True""",
            ctx.guild.id,
        )
        if len(trashed_messages) == 0:
            await ctx.send(t_("You have no trashed messages."))
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
                title=t_("Trashed Messages"),
                description=page,
                color=self.bot.theme_color,
            )
            for page in p.pages
        ]
        await buttons.Paginator(
            ctx,
            embed_pages=embeds,
            delete_after=True,
        ).start()

    @trashcan.command(
        name="empty",
        aliases=["clear"],
        help=t_("Empties the trashcan.", True),
    )
    @has_guild_permissions(manage_messages=True)
    @bot_has_permissions(
        embed_links=True, add_reactions=True, read_message_history=True
    )
    @commands.guild_only()
    async def empty_trashcan(self, ctx: "MyContext"):
        if not await buttons.Confirm(
            ctx, t_("Are you sure you want to untrash all messages?")
        ).start():
            await ctx.send("Cancelled.")
        await self.bot.db.execute(
            """UPDATE messages
            SET trashed=False
            WHERE guild_id=$1 and trashed=True""",
            ctx.guild.id,
        )
        await ctx.send(t_("All messages have been untrashed."))

    @flags.add_flag("--by", type=discord.User)
    @flags.add_flag("--notby", type=discord.User)
    @flags.add_flag("--contains", type=str)
    @flags.command(
        name="purge",
        help=t_("Trashes a large number of messages at once.", True),
    )
    @has_guild_permissions(manage_messages=True)
    @bot_has_permissions(read_message_history=True, embed_links=True)
    @commands.guild_only()
    async def purgetrash(
        self, ctx: "MyContext", limit: converters.myint, **flags
    ) -> None:
        if limit > 200:
            raise commands.BadArgument(
                t_("Can only purge up to 200 messages at once.")
            )
        elif limit < 1:
            raise commands.BadArgument(t_("Must purge at least 1 message."))

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
            title=t_("Purged {0} Messages.").format(total),
            description="\n".join([f"<@{u}>: {c}" for u, c in purged.items()]),
            color=self.bot.theme_color,
        )

        await ctx.send(embed=embed)

    @flags.add_flag("--by", type=discord.User)
    @flags.add_flag("--notby", type=discord.User)
    @flags.add_flag("--contains", type=str)
    @flags.command(
        name="unpurge",
        help=t_("Untrashes a large number of messages at once.", True),
    )
    @has_guild_permissions(manage_messages=True)
    @bot_has_permissions(read_message_history=True, embed_links=True)
    @commands.guild_only()
    async def unpurgetrash(
        self, ctx: "MyContext", limit: converters.myint, **flags
    ) -> None:
        if limit > 200:
            raise commands.BadArgument(
                t_("Can only unpurge up to 200 messages at once.")
            )
        elif limit < 1:
            raise commands.BadArgument(t_("Must unpurge at least 1 message."))

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
            title=t_("Unpurged {0} Messages.").format(total),
            description="\n".join([f"<@{u}>: {c}" for u, c in purged.items()]),
            color=self.bot.theme_color,
        )

        await ctx.send(embed=embed)

    @commands.command(
        name="messageInfo",
        aliases=["mi"],
        help=t_("Shows information on a message.", True),
    )
    @bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def message_info(
        self, ctx: "MyContext", message: converters.PartialGuildMessage
    ) -> None:
        orig = await starboard_funcs.orig_message(self.bot, message.id)
        if not orig:
            raise errors.MessageNotInDatabse()
        if (
            orig["trashed"]
            and not ctx.message.author.guild_permissions.manage_messages
        ):
            await ctx.send(
                t_(
                    "This message was trashed, and you do not have permission "
                    "to view trashed messages (Manage Messages)."
                )
            )
            return
        jump = utils.jump_link(
            orig["id"], orig["channel_id"], orig["guild_id"]
        )
        embed = discord.Embed(
            title=t_("Message Info"),
            color=self.bot.theme_color,
            description=t_(
                "[Jump to Message]({0})\n"
                "Channel: <#{1[channel_id]}>\n"
                "ID: {1[id]} (`{1[channel_id]}-{1[id]}`)\n"
                "Author: <@{1[author_id]}> | `{1[author_id]}`\n"
                "Trashed: {1[trashed]}\n"
                "Frozen: {1[frozen]}"
            ).format(jump, orig),
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
                jump = t_("Not On Starboard")
                points = 0
                forced = False
            else:
                _jump = utils.jump_link(
                    sb_message["id"],
                    sb_message["starboard_id"],
                    orig["guild_id"],
                )
                jump = t_("[Jump]({0})").format(_jump)
                points = sb_message["points"]
                forced = s["id"] in orig["forced"]
            embed.add_field(
                name=s_obj.name,
                value=(
                    f"<#{s['id']}>: {jump}\n"
                    + t_("Points: **{0}**/{1}\nForced: {2}").format(
                        points, s["required"], forced
                    )
                ),
            )

        await ctx.send(embed=embed)


def setup(bot: Bot) -> None:
    bot.add_cog(Utility(bot))
