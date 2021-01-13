import asyncio
from typing import List, Optional, Union

import discord
from discord.ext import commands


def clean_emoji(
    emoji: Union[str, int, discord.Emoji, discord.Reaction]
) -> str:
    if type(emoji) is discord.Emoji:
        return str(emoji.id)
    else:
        return str(emoji)


def convert_emojis(
    emojis: List[Union[str, int]],
    guild: discord.Guild
) -> List[str]:
    result: List[str] = []
    for e in emojis:
        eid = None
        try:
            eid = int(e)
        except ValueError:
            pass

        if eid is not None:
            e_obj = discord.utils.get(guild.emojis, id=eid)
            result.append(str(e_obj))
        else:
            result.append(str(e))
    return result


def pretty_emoji_string(
    emojis: List[Union[str, int]],
    guild: discord.Guild
) -> str:
    converted = convert_emojis(emojis, guild)
    return ' '.join(converted)


async def confirm(
    ctx: commands.Context
) -> Optional[bool]:
    def check(m) -> bool:
        if m.author.id != ctx.message.author.id:
            return False
        if m.channel.id != ctx.channel.id:
            return False
        if not m.content.lower()[0] in ['y', 'n']:
            return False
        return True

    try:
        message = await ctx.bot.wait_for('message', check=check)
    except asyncio.exceptions.TimeoutError:
        await ctx.send("Timed out.")
        return None
    if message.content.lower().startswith('y'):
        return True
    elif message.content.lower().startswith('n'):
        return False
    return await confirm(ctx)
