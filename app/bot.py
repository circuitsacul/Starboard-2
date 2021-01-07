import os
from typing import List
from dotenv import load_dotenv

import discord
from discord.ext import commands
from pretty_help import PrettyHelp

from .database.database import Database
from .cache import Cache

load_dotenv()


class Bot(commands.AutoShardedBot):
    def __init__(self, *args: list, **kwargs: list) -> None:
        self.theme_color: int = kwargs.pop("theme_color")
        self.error_color: int = kwargs.pop("error_color")
        self.token: str = kwargs.pop("token")
        self.custom_owner_ids: List[int] = kwargs.pop("owner_ids")
        self.database: Database = kwargs.pop("database")

        super().__init__(*args, **kwargs)

        self.cache = Cache()

    async def on_message(self, message: discord.Message) -> None:
        pass


EXTENSIONS = [
    'app.cogs.base.base_events',
    'app.cogs.base.base_commands',
    'jishaku'
]
TOKEN = os.getenv("TOKEN")
OWNER_IDS = [int(uid) for uid in os.getenv("OWNER_IDS").split(' ')]
THEME = int(os.getenv("THEME"), 16)
ERROR = int(os.getenv("ERROR"), 16)
HELP_COMMAND = PrettyHelp(
    color=THEME
)
INTENTS = discord.Intents(
    messages=True, members=True,
    guilds=True, reactions=True,
    emojis=True
)
DATABASE = Database(
    os.getenv("DB_NAME"),
    os.getenv("DB_USER"),
    os.getenv("DB_PASSWORD")
)
BOT = Bot(
    token=TOKEN,
    theme_color=THEME,
    error_color=ERROR,
    owner_ids=OWNER_IDS,
    database=DATABASE,
    help_command=HELP_COMMAND,
    command_prefix=commands.when_mentioned_or('sb!'),
    intents=INTENTS
)


async def run() -> None:
    print("Opening Database...")
    await DATABASE.init_database()

    print("Loading Extensions...")
    for ext in EXTENSIONS:
        BOT.load_extension(ext)

    print("Starting Bot...")
    await BOT.start(TOKEN)
