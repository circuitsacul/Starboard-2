import os

import discord
from discord.ext import commands
from dotenv import load_dotenv
from pretty_help import PrettyHelp

import config
from .cache import Cache
from .classes.bot import Bot
from .database.database import Database

load_dotenv()


EXTENSIONS = [
    'app.cogs.base.base_events',
    'app.cogs.base.base_commands',
    'app.cogs.starboard.starboard_commands',
    'jishaku'
]
TOKEN = os.getenv("TOKEN")
OWNER_IDS = config.OWNER_IDS
THEME = config.THEME_COLOR
ERROR = config.ERROR_COLOR
CACHE = Cache()
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
    cache=CACHE,
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
