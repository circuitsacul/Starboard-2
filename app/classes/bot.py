import discord
from discord.ext import commands

from .guild import Guild


class Bot(commands.AutoShardedBot):
    def __init__(self, *args: list, **kwargs: list) -> None:
        self.theme_color = kwargs.pop("theme_color")
        self.error_color = kwargs.pop("error_color")
        self.token = kwargs.pop("token")
        self.custom_owner_ids = kwargs.pop("owner_ids")
        self.database = kwargs.pop("database")
        self.cache = kwargs.pop("cache")

        super().__init__(*args, **kwargs)

    async def on_message(self, message: discord.Message) -> None:
        pass

    async def get_sql_guild(self, guild_id: int):
        guild = self.cache.guilds.get(id=guild_id)
        if guild is None:
            guild = await Guild.from_id(self, guild_id)
        return guild
