import typing

import discord
from discord.abc import GuildChannel
from discord.channel import DMChannel
from discord.ext.commands import Context as DefaultContext

if typing.TYPE_CHECKING:
    from app.classes.bot import Bot


class MyContext(DefaultContext):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message_registered = False

        if typing.TYPE_CHECKING:
            self.bot: "Bot" = self.bot
            self.message: discord.Message = self.message
            self.guild: typing.Optional[discord.Guild] = self.guild
            self.channel: typing.Union[GuildChannel, DMChannel] = self.channel

    async def send(self, *args, **kwargs) -> discord.Message:
        if not self.message_registered:
            self.bot.register_cleanup(self.message)
            self.message_registered = True

        m = await super().send(*args, **kwargs)
        self.bot.register_cleanup(m)
        return m
