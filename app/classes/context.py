import discord
from discord.ext.commands import Context


class CustomContext(Context):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message_registered = False

    async def send(self, *args, **kwargs) -> discord.Message:
        if not self.message_registered:
            self.bot.register_cleanup(self.message)
            self.message_registered = True

        m = await super().send(*args, **kwargs)
        self.bot.register_cleanup(m)
        return m
