import discord
from discord.ext import commands, flags

from app import converters, errors, utils, menus
from app.classes.bot import Bot
from app.cogs.quick_actions import qa_funcs


async def raise_if_exists(emoji: str, ctx: commands.Context) -> None:
    guild = await ctx.bot.db.guilds.get(ctx.guild.id)
    if qa_funcs.get_qa_type(emoji, guild) is not None:
        raise errors.AlreadyExists("That is already a QuickAction!")


class Settings(commands.Cog):
    "Manage settings for a server (not starboard settings)"

    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.command(
        name="disabled",
        brief="Lists disabled commands",
        invoke_without_command=True,
    )
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def disabled_cmds(self, ctx: commands.Context) -> None:
        """Lists all commands that have been disabled"""
        p = ctx.prefix

        guild = await self.bot.db.guilds.get(ctx.guild.id)
        if len(guild["disabled_commands"]) == 0:
            await ctx.send(
                f"No disabled commands. Disable a command with `{p}disable "
                "<command>`"
            )
            return
        string = ""
        for c in guild["disabled_commands"]:
            string += f"`{c}`\n"
        embed = discord.Embed(
            title="Disabled Commands",
            description=string,
            color=self.bot.theme_color,
        ).set_footer(
            text=f"Disable a command with {p}disable <command>\n"
            f"Enable a command with {p}enable <command>"
        )
        await ctx.send(embed=embed)

    @commands.command(name="disable", brief="Disables a command")
    @commands.has_guild_permissions(manage_guild=True)
    async def disable_command(
        self, ctx: commands.Context, command: converters.Command
    ) -> None:
        """Disables a command, so only someone with
        manage_guild permissions can use them"""
        guild = await self.bot.db.guilds.get(ctx.guild.id)
        name = command.qualified_name
        new_commands = guild["disabled_commands"]
        if name in new_commands:
            raise errors.AlreadyExists("That command is already disabled")
        new_commands.append(name)
        await self.bot.db.execute(
            """UPDATE guilds
            SET disabled_commands=$1::text[]
            WHERE id=$2""",
            new_commands,
            ctx.guild.id,
        )
        await ctx.send(f"Disabled `{name}`")

    @commands.command(name="enable", brief="Enables a command")
    @commands.has_guild_permissions(manage_guild=True)
    async def enable_command(
        self, ctx: commands.Context, command: converters.Command
    ) -> None:
        """Enables a command"""
        guild = await self.bot.db.guilds.get(ctx.guild.id)
        name = command.qualified_name
        new_commands = guild["disabled_commands"]
        if name not in new_commands:
            raise errors.DoesNotExist("That command is not disabled")
        new_commands.remove(name)
        await self.bot.db.execute(
            """UPDATE guilds
            SET disabled_commands=$1::text[]
            WHERE id=$2""",
            new_commands,
            ctx.guild.id,
        )
        await ctx.send(f"Enabled `{name}`")

    @commands.command(
        name="settings", aliases=["options"], brief="View guild settings"
    )
    @commands.bot_has_permissions(embed_links=True)
    async def guild_settings(self, ctx: commands.Context) -> None:
        """Lists the settings for the curent server.
        A list of commands to change these settings can
        be viewed by running sb!help Settings"""
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
        embed = discord.Embed(
            title=f"Settings for {ctx.guild.name}",
            description=(
                f"logChannel: {log_channel}\n"
                f"levelChannel: {level_channel}\n"
                f"pingOnLevelUp: **{guild['ping_user']}**\n"
                f"allowCommands: **{guild['allow_commands']}**\n"
                f"quickActionsOn: **{guild['qa_enabled']}**\n"
                f"disabledCommands: **{len(guild['disabled_commands'])}**"
            ),
            color=self.bot.theme_color,
        )
        await ctx.send(embed=embed)

    @commands.group(
        name="quickactions",
        aliases=["qa"],
        brief="Modify quickActions",
        invoke_without_command=True,
    )
    @commands.has_guild_permissions(manage_messages=True)
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def quickactions(self, ctx: commands.Context) -> None:
        """Modify the emojis for quickActions"""
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
        ).set_footer(text=f"To modify these, run {p}help qa")
        await ctx.send(embed=embed)

    @quickactions.command(
        name="enable", aliases=["on", "enabled"], brief="Enables quickActions"
    )
    @commands.has_guild_permissions(manage_messages=True)
    async def enable_quickactions(self, ctx: commands.Context) -> None:
        """Enable quickActions"""
        await self.bot.db.execute(
            """UPDATE guilds SET qa_enabled=True WHERE id=$1""", ctx.guild.id
        )
        await ctx.send("Enabled quickActions")

    @quickactions.command(
        name="disable",
        aliases=["off", "disabled"],
        brief="Disables quickActions",
    )
    @commands.has_guild_permissions(manage_messages=True)
    async def disable_quickactions(self, ctx: commands.Context) -> None:
        """Disable quickActions"""
        await self.bot.db.execute(
            """UPDATE guilds SET qa_enabled=False WHERE id=$1""", ctx.guild.id
        )
        await ctx.send("Disabled quickActions")

    @quickactions.command(
        name="reset", brief="Resets quickActions to their default"
    )
    @commands.has_guild_permissions(manage_messages=True)
    async def reset_quickactions(self, ctx: commands.Context) -> None:
        """Reset quickAction emojis"""
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
        await ctx.send("Reset quickActions")

    @quickactions.command(
        name="force", brief="Sets the force quickAction emoji"
    )
    @commands.has_guild_permissions(manage_messages=True)
    async def force_quickaction(
        self, ctx: commands.Context, emoji: converters.Emoji
    ) -> None:
        """Sets the quickAction emoji for forcing messages"""
        clean = utils.clean_emoji(emoji)
        await raise_if_exists(clean, ctx)
        await self.bot.db.execute(
            """UPDATE guilds
            SET qa_force=$1
            WHERE id=$2""",
            clean,
            ctx.guild.id,
        )
        await ctx.send(f"Set the force emoji to {emoji}")

    @quickactions.command(
        name="unforce", brief="Set the unforce quickAction emoji"
    )
    @commands.has_guild_permissions(manage_messages=True)
    async def unforce_quickaction(
        self, ctx: commands.Context, emoji: converters.Emoji
    ) -> None:
        """Sets the quickAction emoji for unforcing
        messages"""
        clean = utils.clean_emoji(emoji)
        await raise_if_exists(clean, ctx)
        await self.bot.db.execute(
            """UPDATE guilds
            SET qa_unforce=$1
            WHERE id=$2""",
            clean,
            ctx.guild.id,
        )
        await ctx.send(f"Set the unforce emoji to {emoji}")

    @quickactions.command(
        name="freeze",
        aliases=["unfreeze"],
        brief="Sets the freeze/unfreeze emoji",
    )
    @commands.has_guild_permissions(manage_messages=True)
    async def freeze_quickaction(
        self, ctx: commands.Context, emoji: converters.Emoji
    ) -> None:
        """Sets the quickAction emoji for freezing
        and unfreezing messags"""
        clean = utils.clean_emoji(emoji)
        await raise_if_exists(clean, ctx)
        await self.bot.db.execute(
            """UPDATE guilds
            SET qa_freeze=$1
            WHERE id=$2""",
            clean,
            ctx.guild.id,
        )
        await ctx.send(f"Set the freeze/unfreeze emoji to {emoji}")

    @quickactions.command(
        name="trash", brief="Sets the trash/untrash quickAction emoji"
    )
    @commands.has_guild_permissions(manage_messages=True)
    async def trash_quickaction(
        self, ctx: commands.Context, emoji: converters.Emoji
    ) -> None:
        """Sets the quickAction emoji for trashing
        and untrashing messages"""
        clean = utils.clean_emoji(emoji)
        await raise_if_exists(clean, ctx)
        await self.bot.db.execute(
            """UPDATE guilds
            SET qa_trash=$1
            WHERE id=$2""",
            clean,
            ctx.guild.id,
        )
        await ctx.send(f"Set the trash/untrash emoji to {emoji}")

    @quickactions.command(
        name="recount", brief="Sets the recount quickAction emoji"
    )
    @commands.has_guild_permissions(manage_messages=True)
    async def recount_quickaction(
        self, ctx: commands.Context, emoji: converters.Emoji
    ) -> None:
        """Sets the quickAction emoji for recounting message
        reactions"""
        clean = utils.clean_emoji(emoji)
        await raise_if_exists(clean, ctx)
        await self.bot.db.execute(
            """UPDATE guilds
            SET qa_recount=$1
            WHERE id=$2""",
            clean,
            ctx.guild.id,
        )
        await ctx.send(f"Set the recount emoji to {emoji}")

    @quickactions.command(name="save", brief="Sets the save quickAction emoji")
    @commands.has_guild_permissions(manage_messages=True)
    async def save_quickaction(
        self, ctx: commands.Context, emoji: converters.Emoji
    ) -> None:
        """Set the quickAction emoji for saving messages"""
        clean = utils.clean_emoji(emoji)
        await raise_if_exists(clean, ctx)
        await self.bot.db.execute(
            """UPDATE guilds
            SET qa_save=$1
            WHERE id=$2""",
            clean,
            ctx.guild.id,
        )
        await ctx.send(f"Set the save emoji to {emoji}")

    @commands.group(
        name="prefixes",
        aliases=["pfx", "prefix", "p"],
        brief="List and manage prefixes",
        invoke_without_command=True,
    )
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def prefixes(self, ctx: commands.Context) -> None:
        """Lists prefixes for the current server.
        Run sb!help prefixes to view commands for
        modifying the prefixes."""
        guild = await self.bot.db.guilds.get(ctx.guild.id)
        embed = discord.Embed(
            title=f"Prefixes for {ctx.guild.name}",
            description=(
                f"{self.bot.user.mention}\n"
                + "\n".join(f"`{utils.escmd(p)}`" for p in guild["prefixes"])
            ),
            color=self.bot.theme_color,
        )
        await ctx.send(embed=embed)

    @flags.add_flag("--space", action="store_true")
    @prefixes.command(
        cls=flags.FlagCommand, name="add", aliases=["a"], brief="Adds a prefix"
    )
    @commands.has_guild_permissions(manage_messages=True)
    async def add_prefix(
        self, ctx: commands.Context, prefix: str, **options
    ) -> None:
        """Adds a prefix.

        Usage:
            prefixes add <prefix> <options>
        Options:
            --space: Wether or not to add a space at
                the end of the prefix.
        Examples:
            sb!prefixes add star --space
            sb!prefixes add sb?
        """
        if options["space"] is True:
            prefix += " "
        if len(prefix) > 8:
            raise discord.InvalidArgument(
                f"`{prefix}` is too long (max length is 8 characters)."
            )
        guild = await self.bot.db.guilds.get(ctx.guild.id)
        if prefix in guild["prefixes"]:
            raise errors.AlreadyExists(f"`{prefix}` is already a prefix.")
        new_prefixes = guild["prefixes"] + [prefix]
        await self.bot.db.execute(
            """UPDATE guilds
            SET prefixes=$1
            WHERE id=$2""",
            new_prefixes,
            ctx.guild.id,
        )

        await ctx.send(f"Added `{prefix}` to the prefixes.")

    @prefixes.command(
        name="remove", aliases=["rm", "r"], brief="Removes a prefix"
    )
    @commands.has_guild_permissions(manage_messages=True)
    @commands.bot_has_permissions(
        add_reactions=True, read_message_history=True
    )
    @commands.guild_only()
    async def remove_prefix(self, ctx: commands.Context, prefix: str) -> None:
        """Removes a prefix"""
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
                raise discord.InvalidArgument(
                    f"I found {matches} matches for `{prefix}`. "
                    "Please be more specific."
                )
            elif not match:
                raise errors.DoesNotExist(f"No matches found for `{prefix}`")
            else:
                if not await menus.Confirm(
                    f"Did you want to remove `{match}` from the prefixes?"
                ).start(ctx):
                    await ctx.send("Cancelled")
                    return
                to_remove = match
        new_prefixes = guild["prefixes"]
        new_prefixes.remove(to_remove)

        await self.bot.db.execute(
            """UPDATE guilds
            SET prefixes=$1
            WHERE id=$2""",
            new_prefixes,
            ctx.guild.id,
        )

        await ctx.send(f"Removed `{to_remove}` from the prefixes.")

    @prefixes.command(
        name="reset", brief='Removes all prefixes and adds "sb!"'
    )
    @commands.has_guild_permissions(manage_messages=True)
    @commands.bot_has_permissions(
        add_reactions=True, read_message_history=True
    )
    @commands.guild_only()
    async def reset_prefixes(self, ctx: commands.Context) -> None:
        """Deletes all prefixes, then adds the default sb!
        prefix back."""
        if not await menus.Confirm(
            "Are you sure you want to reset all prefixes?"
        ).start(ctx):
            await ctx.send("Cancelled")
            return
        await self.bot.db.execute(
            """UPDATE guilds
            SET prefixes='{"sb!"}'
            WHERE id=$1""",
            ctx.guild.id,
        )
        await ctx.send("Cleared all prefixes and added `sb!`.")

    @commands.command(
        name="levelChannel",
        aliases=["lvlc"],
        brief="Sets the channel for level up messages",
    )
    @commands.has_guild_permissions(manage_guild=True)
    async def set_level_channel(
        self, ctx: commands.Context, channel: discord.TextChannel = None
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
                raise commands.BotMissingPermissions(missing_perms)

        await self.bot.db.execute(
            """UPDATE guilds
            SET level_channel=$1
            WHERE id=$2""",
            channel.id if channel else None,
            ctx.guild.id,
        )
        if channel:
            await ctx.send(f"Set the LevelUpChannel to {channel.mention}.")
        else:
            await ctx.send("Unset the LevelUpChannel.")

    @commands.command(
        name="levelUpPing",
        aliases=["levelPing", "pingOnLevelUp"],
        brief="Whether or not to ping users when they level up",
    )
    @commands.has_guild_permissions(manage_guild=True)
    async def set_level_ping(
        self, ctx: commands.Context, ping: converters.mybool
    ) -> None:
        await self.bot.db.execute(
            """UPDATE guilds SET ping_user=$1 WHERE id=$2""",
            ping,
            ctx.guild.id,
        )
        if ping:
            await ctx.send("I will now ping users when the level up.")
        else:
            await ctx.send("I will not ping users when the level up.")

    @commands.command(
        name="logChannel",
        aliases=["log", "lc"],
        brief="Sets the channel where logs are sent to",
    )
    @commands.has_guild_permissions(manage_guild=True)
    async def set_logchannel(
        self, ctx: commands.Context, channel: discord.TextChannel = None
    ) -> None:
        """Set the log channel of the current server.
        This is where all errors and important info
        will be sent.

        Options:
            channel: What channel to set the log channel to"""
        if channel:
            perms = channel.permissions_for(ctx.guild.me)
            missing_perms = []
            if not perms.read_messages:
                missing_perms.append("Read Messages")
            if not perms.send_messages:
                missing_perms.apppend("Send Messages")
            if not perms.embed_links:
                missing_perms.append("Embed Links")
            if missing_perms != []:
                raise commands.BotMissingPermissions(missing_perms)

        await self.bot.db.execute(
            """UPDATE guilds
            SET log_channel=$1
            WHERE id=$2""",
            channel.id if channel else None,
            ctx.guild.id,
        )
        if channel:
            await ctx.send(f"Set the log channel to {channel.mention}")
            self.bot.dispatch(
                "guild_log",
                "This channel has been set as a log channel. I'll send "
                "errors and important info here.",
                "info",
                ctx.guild,
            )
        else:
            await ctx.send("Unset the log channel.")

    @commands.command(
        name="allowCommands",
        aliases=["ac"],
        brief="Wether or not to allow commands from non-admins",
    )
    @commands.has_guild_permissions(administrator=True)
    async def set_allow_commands(
        self, ctx: commands.Context, value: converters.mybool
    ) -> None:
        await self.bot.db.execute(
            """UPDATE guilds
            SET allow_commands=$1
            WHERE id=$2""",
            value,
            ctx.guild.id,
        )
        await ctx.send(f"Set allowCommands to **{value}**")


def setup(bot: Bot) -> None:
    bot.add_cog(Settings(bot))
