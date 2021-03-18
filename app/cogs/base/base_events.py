import asyncio
import datetime
import os
import traceback
from typing import Any, List

import aiohttp
import discord
from discord import AsyncWebhookAdapter, Webhook
from discord.ext import commands, flags
from dotenv import load_dotenv

from app import utils

from ... import errors
from ...classes.bot import Bot

load_dotenv()

IGNORED_ERRORS = [commands.CommandNotFound, errors.AllCommandsDisabled]
EXPECTED_ERRORS = [
    errors.ConversionError,
    errors.DoesNotExist,
    errors.AlreadyExists,
    errors.CommandDisabled,
    commands.MissingRequiredArgument,
    commands.ChannelNotFound,
    commands.RoleNotFound,
    commands.NotOwner,
    commands.CommandOnCooldown,
    discord.Forbidden,
    discord.InvalidArgument,
    commands.BadArgument,
    commands.NoPrivateMessage,
    commands.UserNotFound,
    commands.RoleNotFound,
    flags.ArgumentParsingError,
]
UPTIME = os.getenv("UPTIME_HOOK")
ERROR = os.getenv("ERROR_HOOK")
GUILD = os.getenv("GUILD_HOOK")


class BaseEvents(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

        self.session: aiohttp.ClientSession = None
        self.guild_webhook: Webhook = None
        self.error_webhook: Webhook = None
        self.uptime_webhook: Webhook = None

        self.type_map = {
            "error": {"color": self.bot.error_color, "title": "Error"},
            "info": {"color": self.bot.theme_color, "title": "Info"},
        }

    def cog_unload(self):
        asyncio.ensure_future(self.session.close())

    async def get_session(self) -> None:
        if self.session:
            return
        self.session = aiohttp.ClientSession()

    async def uptime_log(self, content: str) -> None:
        if not UPTIME:
            return
        await self.get_session()
        if not self.uptime_webhook:
            self.uptime_webhook = Webhook.from_url(
                UPTIME, adapter=AsyncWebhookAdapter(self.session)
            )
        await self.uptime_webhook.send(content, username="Starboard Uptime")

    async def error_log(self, content: str) -> None:
        if not ERROR:
            return
        await self.get_session()
        if not self.error_webhook:
            self.error_webhook = Webhook.from_url(
                ERROR, adapter=AsyncWebhookAdapter(self.session)
            )
        await self.error_webhook.send(content, username="Starboard Errors")

    async def join_leave_log(self, embed: discord.Embed) -> None:
        if not GUILD:
            return
        await self.get_session()
        if not self.guild_webhook:
            self.guild_webhook = Webhook.from_url(
                GUILD, adapter=AsyncWebhookAdapter(self.session)
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
        args: List[Any] = [],
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
        await self.bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching, name="@Starboard for help"
            )
        )
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
        if message.content.replace("!", "") == self.bot.user.mention:
            p = utils.escmd((await self.bot.get_prefix(message))[0])
            await message.channel.send(f"My prefix is `{p}`")
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
        if type(e) in IGNORED_ERRORS:
            return
        elif type(e) in EXPECTED_ERRORS:
            await ctx.send(e)
        elif type(e) == discord.errors.Forbidden:
            try:
                await ctx.message.author.send(
                    "I can't send messages in "
                    f"{ctx.message.channel.mention}, "
                    "or I'm missing the `Embed Links` "
                    "permission there."
                )
            except discord.Forbidden:
                pass
        else:
            embed = discord.Embed(
                title="Something's Not Right",
                description=(
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
            await ctx.send(embed=embed)

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
            title=f"{user.name} Leveled up!",
            description=f"They are now level **{level}**!",
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
    async def create_data(message: discord.Message) -> None:
        if message.guild is None:
            return
        await bot.db.guilds.create(message.guild.id)
        await bot.db.users.create(message.author.id, message.author.bot)
        await bot.db.members.create(message.author.id, message.guild.id)
