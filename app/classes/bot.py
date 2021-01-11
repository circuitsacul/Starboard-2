import discord
from discord.ext import commands

from ..database.database import Database


class Bot(commands.AutoShardedBot):
    def __init__(self, *args: list, **kwargs: list) -> None:
        self.theme_color = kwargs.pop("theme_color")
        self.error_color = kwargs.pop("error_color")
        self.token = kwargs.pop("token")
        self.custom_owner_ids = kwargs.pop("owner_ids")
        self.db: Database = kwargs.pop("database")
        self.cache = kwargs.pop("cache")

        super().__init__(*args, **kwargs)

    async def on_message(self, message: discord.Message) -> None:
        pass
