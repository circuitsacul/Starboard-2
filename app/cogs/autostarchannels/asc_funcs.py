import discord

from app import utils


async def handle_message(
    message: discord.Message, aschannel: dict
) -> None:
    emojis = utils.convert_emojis(aschannel['emojis'], message.guild)
    for e in emojis:
        await message.add_reaction(e)
