import discord
from discord.ext.commands import Context


class CustomContext(Context):
    async def send(self, *args, **kwargs) -> discord.Message:
        m = await super().send(*args, **kwargs)
        self.bot.register_cleanup(m)
        return m
