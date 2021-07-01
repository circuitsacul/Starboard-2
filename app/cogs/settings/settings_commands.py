import discord
from discord.ext.prettyhelp import bot_has_permissions, has_guild_permissions

from app import commands, converters, errors, flags, i18n, menus, utils
from app.classes.bot import Bot
from app.classes.context import MyContext
from app.cogs.quick_actions import qa_funcs
from app.i18n import t_


async def raise_if_exists(emoji: str, ctx: "MyContext") -> None:
    guild = await ctx.bot.db.guilds.get(ctx.guild.id)
    if qa_funcs.get_qa_type(emoji, guild) is not None:
        raise errors.AlreadyQuickAction()


class Settings(
    commands.Cog, description=t_("Manage settings for the server.", True)
):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.command(
        name="guildlanguage",
        aliases=["guildlang"],
        help=t_("Set the language for the server.", True),
    )
    @has_guild_permissions(manage_guild=True)
    @commands.guild_only()
    async def set_guild_lang(
        self, ctx: "MyContext", locale: converters.language = None
    ) -> None:
        if not locale:
            await ctx.send(
                embed=i18n.language_embed(self.bot, utils.clean_prefix(ctx))
            )
            return

        code, name = locale

        await self.bot.db.guilds.set_locale(ctx.guild.id, code)
        if ctx.guild.id in self.bot.locale_cache:
            self.bot.locale_cache[ctx.guild.id] = code
        await ctx.send(
            t_("Set the language for this server to {0}.").format(name)
        )

    @commands.command(
        name="disabled",
        help=t_("Lists disabled commands.", True),
    )
    @bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def disabled_cmds(self, ctx: "MyContext") -> None:
        p = ctx.prefix

        guild = await self.bot.db.guilds.get(ctx.guild.id)
        if len(guild["disabled_commands"]) == 0:
            await ctx.send(
                t_(
                    "No disabled commands. Disable a command with `{0}disable "
                    "<command>`."
                ).format(p)
            )
            return
        string = ""
        for c in guild["disabled_commands"]:
            string += f"`{c}`\n"
        embed = discord.Embed(
            title=t_("Disabled Commands:"),
            description=string,
            color=self.bot.theme_color,
        ).set_footer(
            text=t_(
                "Disable a command with `{0}disable <command>`.\n"
                "Enable a command with `{0}enable <command>`."
            ).format(p)
        )
        await ctx.send(embed=embed)

    @commands.command(name="disable", help=t_("Disables a command.", True))
    @has_guild_permissions(manage_guild=True)
    async def disable_command(
        self, ctx: "MyContext", command: converters.Command
    ) -> None:
        guild = await self.bot.db.guilds.get(ctx.guild.id)
        name = command.qualified_name
        new_commands = guild["disabled_commands"]
        if name in new_commands:
            raise errors.AlreadyDisabled(name)
        new_commands.append(name)
        await self.bot.db.execute(
            """UPDATE guilds
            SET disabled_commands=$1::text[]
            WHERE id=$2""",
            new_commands,
            ctx.guild.id,
        )
        await ctx.send(t_("Disabled `{0}`.").format(name))

    @commands.command(name="enable", help=t_("Enables a command.", True))
    @has_guild_permissions(manage_guild=True)
    async def enable_command(
        self, ctx: "MyContext", command: converters.Command
    ) -> None:
        guild = await self.bot.db.guilds.get(ctx.guild.id)
        name = command.qualified_name
        new_commands = guild["disabled_commands"]
        if name not in new_commands:
            raise errors.NotDisabled(name)
        new_commands.remove(name)
        await self.bot.db.execute(
            """UPDATE guilds
            SET disabled_commands=$1::text[]
            WHERE id=$2""",
            new_commands,
            ctx.guild.id,
        )
        await ctx.send(t_("Enabled `{0}`.").format(name))

    @commands.command(
        name="settings",
        aliases=["options"],
        help=t_("View guild settings.", True),
    )
    @bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def guild_settings(self, ctx: "MyContext") -> None:
        guild = await self.bot.db.guilds.get(ctx.guild.id)
        log_channel = (
            "**None**"
            if guild["log_channel"] is None
            else f"<#{guild['log_channel']}>"
        )
        level_channel = (
            "**None**"
            if guild["level_channel"] is None
            else f"<#{guild['level_channel']}>"
        )
        enabled_str = (
            t_("enabled") if guild["xp_cooldown_on"] else t_("disabled")
        )
        embed = discord.Embed(
            title=t_("Settings for {0}:").format(ctx.guild.name),
            description=(
                f"language: **{guild['locale']}**\n"
                f"logChannel: {log_channel}\n"
                f"levelChannel: {level_channel}\n"
                f"pingOnLevelUp: **{guild['ping_user']}**\n"
                f"allowCommands: **{guild['allow_commands']}**\n"
                f"quickActionsOn: **{guild['qa_enabled']}**\n"
                f"cooldown: **{guild['xp_cooldown']}**"
                f"/**{guild['xp_cooldown_per']}**s "
                f"(**{enabled_str}**)\n"
                f"disabledCommands: **{len(guild['disabled_commands'])}**\n"
            ),
            color=self.bot.theme_color,
        )
        await ctx.send(embed=embed)

    @commands.group(
        name="cooldown",
        help=t_("Sets the cooldown for xp.", True),
        invoke_without_command=True,
    )
    @has_guild_permissions(manage_messages=True)
    @bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def set_cooldown(
        self,
        ctx: "MyContext",
        ammount: converters.myint,
        per: converters.myint,
    ):
        sql_guild = await self.bot.db.guilds.get(ctx.guild.id)
        await self.bot.db.guilds.set_cooldown(ctx.guild.id, ammount, per)

        orig = (
            f"**{sql_guild['xp_cooldown']}**/"
            f"**{sql_guild['xp_cooldown_per']}**s"
        )
        new = f"**{ammount}**/**{per}**s"

        await ctx.send(
            embed=utils.cs_embed(
                {"cooldown": (orig, new)}, self.bot, noticks=True
            )
        )

    @set_cooldown.command(name="disable", help=t_("Disables the XP cooldown."))
    @has_guild_permissions(manage_messages=True)
    @bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def disable_cooldown(self, ctx: "MyContext"):
        await self.bot.db.guilds.set_cooldown_enabled(ctx.guild.id, False)
        await ctx.send(t_("Disabled the XP cooldown."))

    @set_cooldown.command(name="enable", help=t_("Enables the XP cooldown."))
    @has_guild_permissions(manage_messages=True)
    @bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def enable_cooldown(self, ctx: "MyContext"):
        await self.bot.db.guilds.set_cooldown_enabled(ctx.guild.id, True)
        await ctx.send(t_("Enabled the XP cooldown."))

    @commands.group(
        name="quickactions",
        aliases=["qa"],
        help=t_("Modify QuickActions.", True),
        invoke_without_command=True,
    )
    @has_guild_permissions(manage_messages=True)
    @bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def quickactions(self, ctx: "MyContext") -> None:
        p = ctx.prefix
        guild = await self.bot.db.guilds.get(ctx.guild.id)
        embed = discord.Embed(
            title="QuickActions",
            description=(
                f"enabled: **{guild['qa_enabled']}**\n"
                f"force: {guild['qa_force']}\n"
                f"unforce: {guild['qa_unforce']}\n"
                f"freeze: {guild['qa_freeze']}\n"
                f"trash: {guild['qa_trash']}\n"
                f"recount: {guild['qa_recount']}\n"
                f"save: {guild['qa_save']}\n"
            ),
            color=self.bot.theme_color,
        ).set_footer(text=t_("To modify these, run `{0}help qa`.").format(p))
        await ctx.send(embed=embed)

    @quickactions.command(
        name="enable",
        aliases=["on", "enabled"],
        help=t_("Enables QuickActions.", True),
    )
    @has_guild_permissions(manage_messages=True)
    async def enable_quickactions(self, ctx: "MyContext") -> None:
        await self.bot.db.execute(
            """UPDATE guilds SET qa_enabled=True WHERE id=$1""", ctx.guild.id
        )
        await ctx.send(t_("Enabled QuickActions."))

    @quickactions.command(
        name="disable",
        aliases=["off", "disabled"],
        help=t_("Disables QuickActions.", True),
    )
    @has_guild_permissions(manage_messages=True)
    async def disable_quickactions(self, ctx: "MyContext") -> None:
        await self.bot.db.execute(
            """UPDATE guilds SET qa_enabled=False WHERE id=$1""", ctx.guild.id
        )
        await ctx.send(t_("Disabled QuickActions."))

    @quickactions.command(
        name="reset", help=t_("Resets QuickActions to their default.", True)
    )
    @has_guild_permissions(manage_messages=True)
    async def reset_quickactions(self, ctx: "MyContext") -> None:
        await self.bot.db.execute(
            """UPDATE guilds
            SET qa_force='🔒',
            qa_unforce='🔓',
            qa_freeze='❄️',
            qa_trash='🗑️',
            qa_recount='🔃',
            qa_save='📥'
            WHERE id=$1""",
            ctx.guild.id,
        )
        await ctx.send(t_("Reset quickActions."))

    @quickactions.command(
        name="force", help=t_("Sets the force QuickAction emoji.", True)
    )
    @has_guild_permissions(manage_messages=True)
    async def force_quickaction(
        self, ctx: "MyContext", emoji: converters.Emoji
    ) -> None:
        clean = utils.clean_emoji(emoji)
        await raise_if_exists(clean, ctx)
        await self.bot.db.execute(
            """UPDATE guilds
            SET qa_force=$1
            WHERE id=$2""",
            clean,
            ctx.guild.id,
        )
        await ctx.send(t_("Set the force QuickAction to {0}.").format(emoji))

    @quickactions.command(
        name="unforce", help=t_("Set the unforce QuickAction emoji.", True)
    )
    @has_guild_permissions(manage_messages=True)
    async def unforce_quickaction(
        self, ctx: "MyContext", emoji: converters.Emoji
    ) -> None:
        clean = utils.clean_emoji(emoji)
        await raise_if_exists(clean, ctx)
        await self.bot.db.execute(
            """UPDATE guilds
            SET qa_unforce=$1
            WHERE id=$2""",
            clean,
            ctx.guild.id,
        )
        await ctx.send(t_("Set the unforce QuickAction to {0}.").format(emoji))

    @quickactions.command(
        name="freeze",
        aliases=["unfreeze"],
        help=t_("Sets the freeze/unfreeze QuickAction emoji.", True),
    )
    @has_guild_permissions(manage_messages=True)
    async def freeze_quickaction(
        self, ctx: "MyContext", emoji: converters.Emoji
    ) -> None:
        clean = utils.clean_emoji(emoji)
        await raise_if_exists(clean, ctx)
        await self.bot.db.execute(
            """UPDATE guilds
            SET qa_freeze=$1
            WHERE id=$2""",
            clean,
            ctx.guild.id,
        )
        await ctx.send(
            t_("Set the freeze/unfreeze QuickAction to {0}.").format(emoji)
        )

    @quickactions.command(
        name="trash",
        help=t_("Sets the trash/untrash QuickAction emoji.", True),
    )
    @has_guild_permissions(manage_messages=True)
    async def trash_quickaction(
        self, ctx: "MyContext", emoji: converters.Emoji
    ) -> None:
        clean = utils.clean_emoji(emoji)
        await raise_if_exists(clean, ctx)
        await self.bot.db.execute(
            """UPDATE guilds
            SET qa_trash=$1
            WHERE id=$2""",
            clean,
            ctx.guild.id,
        )
        await ctx.send(
            t_("Set the trash/untrash QuickAction to {0}.").format(emoji)
        )

    @quickactions.command(
        name="recount", help=t_("Sets the recount QuickAction emoji.", True)
    )
    @has_guild_permissions(manage_messages=True)
    async def recount_quickaction(
        self, ctx: "MyContext", emoji: converters.Emoji
    ) -> None:
        clean = utils.clean_emoji(emoji)
        await raise_if_exists(clean, ctx)
        await self.bot.db.execute(
            """UPDATE guilds
            SET qa_recount=$1
            WHERE id=$2""",
            clean,
            ctx.guild.id,
        )
        await ctx.send(t_("Set the recount QuickAction to {0}.").format(emoji))

    @quickactions.command(
        name="save", help=t_("Sets the save QuickAction emoji.", True)
    )
    @has_guild_permissions(manage_messages=True)
    async def save_quickaction(
        self, ctx: "MyContext", emoji: converters.Emoji
    ) -> None:
        clean = utils.clean_emoji(emoji)
        await raise_if_exists(clean, ctx)
        await self.bot.db.execute(
            """UPDATE guilds
            SET qa_save=$1
            WHERE id=$2""",
            clean,
            ctx.guild.id,
        )
        await ctx.send(t_("Set the save QuickAction to {0}.").format(emoji))

    @commands.group(
        name="prefixes",
        aliases=["pfx", "prefix", "p"],
        help=t_("List and manage prefixes.", True),
        invoke_without_command=True,
    )
    @bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def prefixes(self, ctx: "MyContext") -> None:
        guild = await self.bot.db.guilds.get(ctx.guild.id)
        embed = discord.Embed(
            title=t_("Prefixes for {0}:").format(ctx.guild.name),
            description=(
                f"{self.bot.user.mention}\n"
                + "\n".join(f"`{utils.escmd(p)}`" for p in guild["prefixes"])
            ),
            color=self.bot.theme_color,
        )
        await ctx.send(embed=embed)

    @flags.add_flag("--space", action="store_true")
    @prefixes.command(
        cls=flags.FlagCommand,
        name="add",
        aliases=["a"],
        help=t_("Adds a prefix.", True),
    )
    @has_guild_permissions(manage_messages=True)
    async def add_prefix(
        self, ctx: "MyContext", prefix: str, **options
    ) -> None:
        if options["space"] is True:
            prefix += " "
        await self.bot.db.guilds.add_prefix(ctx.guild.id, prefix)

        await ctx.send(t_("Added `{0}` to the prefixes.").format(prefix))

    @prefixes.command(
        name="remove", aliases=["rm", "r"], help=t_("Removes a prefix.", True)
    )
    @has_guild_permissions(manage_messages=True)
    @bot_has_permissions(add_reactions=True, read_message_history=True)
    @commands.guild_only()
    async def remove_prefix(self, ctx: "MyContext", prefix: str) -> None:
        to_remove = prefix
        guild = await self.bot.db.guilds.get(ctx.guild.id)
        if prefix not in guild["prefixes"]:
            matches = 0
            match = None
            for p in guild["prefixes"]:
                if p.startswith(prefix):
                    matches += 1
                    match = p
            if matches > 1:
                await ctx.send(
                    t_(
                        "I found {0} matches for `{1}`. "
                        "Please be more specific."
                    ).format(matches, prefix)
                )
                return
            elif not match:
                await ctx.send(
                    t_("No matches found for `{0}`.").format(prefix)
                )
                return
            else:
                if not await menus.Confirm(
                    t_(
                        "Did you want to remove `{0}` from the prefixes?"
                    ).format(match),
                ).start(ctx):
                    await ctx.send(t_("Cancelled."))
                    return
                to_remove = match
        await self.bot.db.guilds.remove_prefix(ctx.guild.id, to_remove)

        await ctx.send(
            t_("Removed `{0}` from the prefixes.").format(to_remove)
        )

    @prefixes.command(
        name="reset", help=t_('Removes all prefixes and adds "sb!".', True)
    )
    @has_guild_permissions(manage_messages=True)
    @bot_has_permissions(add_reactions=True, read_message_history=True)
    @commands.guild_only()
    async def reset_prefixes(self, ctx: "MyContext") -> None:
        if not await menus.Confirm(
            t_("Are you sure you want to reset all prefixes?")
        ).start(ctx):
            await ctx.send(t_("Cancelled."))
            return
        await self.bot.db.execute(
            """UPDATE guilds
            SET prefixes='{"sb!"}'
            WHERE id=$1""",
            ctx.guild.id,
        )
        await self.bot.db.guilds.cache.delete(ctx.guild.id)
        await ctx.send(t_("Cleared all prefixes and added `sb!`."))

    @commands.command(
        name="levelChannel",
        aliases=["lvlc"],
        help=t_("Sets the channel for level up messages.", True),
    )
    @has_guild_permissions(manage_guild=True)
    async def set_level_channel(
        self, ctx: "MyContext", channel: discord.TextChannel = None
    ) -> None:
        if channel:
            perms = channel.permissions_for(ctx.guild.me)
            missing_perms = []
            if not perms.read_messages:
                missing_perms.append("Read Messages")
            if not perms.send_messages:
                missing_perms.append("Send Messages")
            if not perms.embed_links:
                missing_perms.append("Embed Links")
            if missing_perms:
                await ctx.send(
                    t_(
                        "I need the following permissions in {0} in order to "
                        "set that as the levelUpChannel:\n{1}"
                    ).format(channel.mention, ", ".join(missing_perms))
                )
                return

        await self.bot.db.execute(
            """UPDATE guilds
            SET level_channel=$1
            WHERE id=$2""",
            channel.id if channel else None,
            ctx.guild.id,
        )
        if channel:
            await ctx.send(
                t_("Set the LevelUpChannel to {0}.").format(channel.mention)
            )
        else:
            await ctx.send(t_("Unset the LevelUpChannel."))

    @commands.command(
        name="levelUpPing",
        aliases=["levelPing", "pingOnLevelUp"],
        help=t_("Whether or not to ping users when they level up.", True),
    )
    @has_guild_permissions(manage_guild=True)
    async def set_level_ping(
        self, ctx: "MyContext", ping: converters.mybool
    ) -> None:
        await self.bot.db.execute(
            """UPDATE guilds SET ping_user=$1 WHERE id=$2""",
            ping,
            ctx.guild.id,
        )
        if ping:
            await ctx.send(t_("I will now ping users when they level up."))
        else:
            await ctx.send(t_("I will not ping users when they level up."))

    @commands.command(
        name="logChannel",
        aliases=["log", "lc"],
        help=t_("Sets the channel where logs are sent to.", True),
    )
    @has_guild_permissions(manage_guild=True)
    async def set_logchannel(
        self, ctx: "MyContext", channel: discord.TextChannel = None
    ) -> None:
        if channel:
            perms = channel.permissions_for(ctx.guild.me)
            missing_perms = []
            if not perms.read_messages:
                missing_perms.append("Read Messages")
            if not perms.send_messages:
                missing_perms.append("Send Messages")
            if not perms.embed_links:
                missing_perms.append("Embed Links")
            if missing_perms != []:
                await ctx.send(
                    t_(
                        "I need the following permissions in {0} in order "
                        "to set that as the log channel:\n{1}"
                    ).format(channel.mention, ", ".join(missing_perms))
                )
                return

        await self.bot.db.execute(
            """UPDATE guilds
            SET log_channel=$1
            WHERE id=$2""",
            channel.id if channel else None,
            ctx.guild.id,
        )
        await self.bot.db.guilds.cache.delete(ctx.guild.id)
        if channel:
            await ctx.send(
                t_("Set the log channel to {0}.").format(channel.mention)
            )
            async with self.bot.temp_locale(ctx.guild):
                self.bot.dispatch(
                    "guild_log",
                    t_(
                        "This channel has been set as a log channel. I'll "
                        "send errors and important info here."
                    ),
                    "info",
                    ctx.guild,
                )
        else:
            await ctx.send("Unset the log channel.")

    @commands.command(
        name="allowCommands",
        aliases=["ac"],
        help=t_("Whether or not to allow commands from non-admins.", True),
    )
    @has_guild_permissions(administrator=True)
    async def set_allow_commands(
        self, ctx: "MyContext", value: converters.mybool
    ) -> None:
        await self.bot.db.execute(
            """UPDATE guilds
            SET allow_commands=$1
            WHERE id=$2""",
            value,
            ctx.guild.id,
        )
        await ctx.send(t_("Set allowCommands to **{0}**.").format(value))


def setup(bot: Bot) -> None:
    bot.add_cog(Settings(bot))
