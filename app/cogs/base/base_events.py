import discord
from discord.ext import commands

from ...bot import Bot


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


def setup(bot: Bot) -> None:
    bot.add_cog(BaseEvents(bot))
