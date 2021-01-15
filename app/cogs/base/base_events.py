import traceback

import aiohttp
import discord
from discord import AsyncWebhookAdapter, Webhook
from discord.ext import commands, flags
from dotenv import load_dotenv

import config

from ... import errors
from ...classes.bot import Bot

IGNORED_ERRORS = [
    commands.CommandNotFound,
]
EXPECTED_ERRORS = [
    errors.ConversionError,
    errors.DoesNotExist,
    errors.AlreadyExists,
    commands.MissingRequiredArgument,
    commands.ChannelNotFound,
    commands.RoleNotFound,
    commands.NotOwner,
    discord.InvalidArgument,
    flags.ArgumentParsingError
]
WEBHOOK_URL = config.UPTIME_WEBHOOK

load_dotenv()


async def webhooklog(content: str) -> None:
    if not WEBHOOK_URL:
        return
    async with aiohttp.ClientSession() as session:
        webhook = Webhook.from_url(
            WEBHOOK_URL, adapter=AsyncWebhookAdapter(session)
        )
        await webhook.send(content, username='Starboard Logs')


class BaseEvents(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_shard_ready(self, shard_id: int) -> None:
        self.bot.log.info(
            f"[Cluster#{self.bot.cluster_name}] Shard {shard_id} ready"
        )

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        self.bot.log.info(
            f"[Cluster#{self.bot.cluster_name}] Ready"
        )
        await webhooklog(
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
        if message.content.replace('!', '') == \
                self.bot.user.mention:
            await message.channel.send("My prefix is `sb!`")
        else:
            await self.bot.process_commands(message)

    @commands.Cog.listener()
    async def on_command_error(
        self,
        ctx: commands.Context,
        e: Exception
    ) -> None:
        try:
            e = e.original
        except AttributeError:
            pass
        if type(e) in IGNORED_ERRORS:
            return
        if type(e) in EXPECTED_ERRORS:
            await ctx.send(e)
        else:
            embed = discord.Embed(
                title="Something's Not Right",
                description=(
                    "Something went wrong while "
                    "running this command. If the "
                    "problem persists, please report "
                    "this in the support server."
                ),
                color=self.bot.error_color
            )
            tb = ''.join(traceback.format_tb(e.__traceback__))
            full_tb = (
                f"{e}\b"
                f"```{tb}```"
            )
            if len(full_tb) > 1024:
                to_remove = (len(full_tb) - 1024) + 10
                full_tb = (
                    f"{e}\n```...{tb[to_remove:]}```"
                )
            embed.add_field(
                name=e.__class__.__name__,
                value=full_tb
            )
            await ctx.send(embed=embed)


def setup(bot: Bot) -> None:
    bot.add_cog(BaseEvents(bot))

    @bot.before_invoke
    async def create_data(
        message: discord.Message
    ) -> None:
        await bot.db.create_guild(message.guild.id)
        await bot.db.create_user(
            message.author.id,
            message.author.bot
        )
        await bot.db.create_member(
            message.author.id, message.guild.id
        )
