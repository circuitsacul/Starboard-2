import traceback

import discord
from discord.ext import commands

from ...classes.bot import Bot
from ... import errors


IGNORED_ERRORS = [
    commands.CommandNotFound
]
EXPECTED_ERRORS = [
    errors.ConversionError,
    errors.DoesNotExist,
    errors.AlreadyExists
]


class BaseEvents(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

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
    async def on_shard_ready(self, shard_id: int) -> None:
        print(f" - Shard {shard_id} ready")

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        print(
            f"Logged in as {self.bot.user.name} in "
            f"{len(self.bot.guilds)} guilds!"
        )

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
            embed.add_field(
                name=e.__class__.__name__,
                value=(
                    f"{e}\n"
                    f"```{''.join(traceback.format_tb(e.__traceback__))}```"
                )
            )
            await ctx.send(embed=embed)


def setup(bot: Bot) -> None:
    bot.add_cog(BaseEvents(bot))
