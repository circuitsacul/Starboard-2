import datetime
import os
import traceback
from typing import Any

import discord
from discord import AsyncWebhookAdapter, Webhook
from discord.ext import commands, flags
from dotenv import load_dotenv

from app import utils
from app.i18n import t_

from ... import errors
from ...classes.bot import Bot

load_dotenv()

IGNORED_ERRORS = (
    commands.CommandNotFound,
    commands.DisabledCommand,
    errors.AllCommandsDisabled,
    errors.CannotUseCommands,
    errors.SupportServerOnly,
)
SEND_HELP = (
    errors.MissingRequiredArgument,
    flags.ArgumentParsingError,
)
EXPECTED_ERRORS = (
    commands.BadArgument,
    commands.NotOwner,
    commands.UserInputError,
    commands.CheckFailure,
    errors.CommandOnCooldown,
    flags.ArgumentParsingError,
)
UPTIME = os.getenv("UPTIME_HOOK")
ERROR = os.getenv("ERROR_HOOK")
GUILD = os.getenv("GUILD_HOOK")


class BaseEvents(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

        self.guild_webhook: Webhook = None
        self.error_webhook: Webhook = None
        self.uptime_webhook: Webhook = None

        self.type_map = {
            "error": {"color": self.bot.error_color, "title": "Error"},
            "info": {"color": self.bot.theme_color, "title": "Info"},
        }

    async def uptime_log(self, content: str) -> None:
        if not UPTIME:
            return
        if not self.uptime_webhook:
            self.uptime_webhook = Webhook.from_url(
                UPTIME, adapter=AsyncWebhookAdapter(self.bot.session)
            )
        await self.uptime_webhook.send(content, username="Starboard Uptime")

    async def error_log(self, content: str) -> None:
        if not ERROR:
            return
        if not self.error_webhook:
            self.error_webhook = Webhook.from_url(
                ERROR, adapter=AsyncWebhookAdapter(self.bot.session)
            )
        await self.error_webhook.send(content, username="Starboard Errors")

    async def join_leave_log(self, embed: discord.Embed) -> None:
        if not GUILD:
            return
        if not self.guild_webhook:
            self.guild_webhook = Webhook.from_url(
                GUILD, adapter=AsyncWebhookAdapter(self.bot.session)
            )
        await self.guild_webhook.send(
            embed=embed, username="Starboard Guild Log"
        )

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild) -> None:
        embed = discord.Embed(
            title=f"Joined **{guild.name}**",
            description=f"**{guild.member_count} members**",
            color=self.bot.theme_color,
        )
        embed.timestamp = datetime.datetime.utcnow()
        await self.join_leave_log(embed)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild) -> None:
        embed = discord.Embed(
            title=f"Left **{guild.name}**",
            description=f"**{guild.member_count} members**",
            color=self.bot.dark_theme_color,
        )
        embed.timestamp = datetime.datetime.utcnow()
        await self.join_leave_log(embed)

    @commands.Cog.listener()
    async def on_log_error(
        self,
        title: str,
        error: Exception,
        args: list[Any] = [],
        kwargs: dict = {},
    ) -> None:
        p = commands.Paginator(prefix="```python")

        p.add_line(title)
        p.add_line(empty=True)
        p.add_line(f"{type(error)}: {error}")
        p.add_line(empty=True)
        p.add_line(f"Args: {args}")
        p.add_line(f"Kwargs: {kwargs}")
        p.add_line(empty=True)

        tb = traceback.format_tb(error.__traceback__)
        for line in tb:
            p.add_line(line=line)

        for page in p.pages:
            await self.error_log(page)

    @commands.Cog.listener()
    async def on_shard_ready(self, shard_id: int) -> None:
        self.bot.log.info(
            f"[Cluster#{self.bot.cluster_name}] Shard {shard_id} ready"
        )

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        self.bot.log.info(f"[Cluster#{self.bot.cluster_name}] Ready")
        await self.uptime_log(
            f":green_circle: Cluster **{self.bot.cluster_name}** ready!"
        )
        try:
            self.bot.pipe.send(1)
        except BrokenPipeError:
            pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        await self.bot.set_locale(message.author)
        if message.content.replace("!", "") == self.bot.user.mention:
            prefixes = await self.bot._prefix_callable(
                self.bot, message, False
            )
            if not prefixes:
                prefix = utils.clean_prefix_no_ctx(
                    self.bot.user.mention + " ", self.bot.user
                )
            else:
                prefix = utils.escmd(prefixes[0])
            await message.channel.send(
                t_("My prefix is `{0}`.").format(prefix)
            )
        else:
            await self.bot.process_commands(message)

    @commands.Cog.listener()
    async def on_command_error(
        self, ctx: commands.Context, e: Exception
    ) -> None:
        try:
            e = e.original
        except AttributeError:
            pass

        e = errors.convert_error(e)

        if isinstance(e, IGNORED_ERRORS):
            return
        elif isinstance(e, EXPECTED_ERRORS):
            try:
                if isinstance(e, SEND_HELP):
                    p = utils.clean_prefix(ctx)
                    await ctx.send(
                        f"{e}\n\n```{p}{ctx.command} "
                        f"{ctx.command.signature}```"
                    )
                else:
                    await ctx.send(e)
            except discord.Forbidden:
                await ctx.message.author.send(
                    t_(
                        "I don't have permission to send messages in "
                        "{0}, so I can't respond to your command."
                    ).format(ctx.channel.mention)
                )
        else:
            embed = discord.Embed(
                title=t_("Something's Not Right"),
                description=t_(
                    "Something went wrong while "
                    "running this command. If the "
                    "problem persists, please report "
                    "this in the support server."
                ),
                color=self.bot.error_color,
            )
            tb = "".join(traceback.format_tb(e.__traceback__))
            full_tb = f"{e}\b" f"```{tb}```"
            if len(full_tb) > 1024:
                to_remove = (len(full_tb) - 1024) + 10
                full_tb = f"{e}\n```...{tb[to_remove:]}```"
            embed.add_field(name=e.__class__.__name__, value=full_tb)
            try:
                await ctx.send(embed=embed)
            except discord.Forbidden:
                pass

            self.bot.dispatch(
                "log_error", "Command Error", e, ctx.args, ctx.kwargs
            )

    @commands.Cog.listener()
    async def on_guild_log(
        self, message: str, log_type: str, guild: discord.Guild
    ) -> None:
        sql_guild = await self.bot.db.guilds.get(guild.id)
        if sql_guild["log_channel"] is None:
            return
        log_channel = guild.get_channel(int(sql_guild["log_channel"]))
        if not log_channel:
            return

        embed = discord.Embed(
            title=self.type_map[log_type]["title"],
            description=message,
            color=self.type_map[log_type]["color"],
        )
        embed.timestamp = datetime.datetime.utcnow()
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_level_up(
        self, guild: discord.Guild, user: discord.User, level: int
    ) -> None:
        sql_guild = await self.bot.db.guilds.get(guild.id)
        if sql_guild["level_channel"] is None:
            return
        level_channel = guild.get_channel(int(sql_guild["level_channel"]))
        if not level_channel:
            return
        embed = discord.Embed(
            title=t_("{0} Leveled up!").format(user.name),
            description=t_("They are now level **{0}**!").format(level),
            color=self.bot.theme_color,
        ).set_author(name=str(user), icon_url=user.avatar_url)
        embed.timestamp = datetime.datetime.utcnow()
        await level_channel.send(
            content=f"{user.mention}" if sql_guild["ping_user"] else "",
            embed=embed,
            allowed_mentions=discord.AllowedMentions(users=True),
        )


def setup(bot: Bot) -> None:
    bot.add_cog(BaseEvents(bot))

    @bot.before_invoke
    async def before_invoke(ctx: commands.Context) -> None:
        if ctx.guild is None:
            return

        await bot.db.guilds.create(ctx.guild.id)
        await bot.db.users.create(ctx.author.id, ctx.author.bot)
        await bot.db.members.create(ctx.author.id, ctx.guild.id)
