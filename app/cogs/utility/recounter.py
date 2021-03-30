import discord

from app import utils
from app.classes.bot import Bot
from app.cogs.starboard import starboard_funcs


def needs_recount(
    message: discord.Message, sbemojis: list[str], min_reactions: int
) -> bool:
    for r in message.reactions:
        if r.emoji not in sbemojis:
            continue
        if r.count < min_reactions:
            continue
        return True
    return False


async def recount_reactions(
    bot: Bot, message: discord.Message, sbemojis: list[str] = None
) -> None:
    if not sbemojis:
        starboards = await bot.db.starboards.get_many(message.guild.id)
        sbemojis = [e for s in starboards for e in s["star_emojis"]]

    for reaction in message.reactions:
        clean = utils.clean_emoji(reaction)
        if clean not in sbemojis:
            continue

        async for user in reaction.users():
            if user.bot:
                continue
            await bot.db.users.create(user.id, user.bot)
            await bot.db.members.create(user.id, message.guild.id)
            await bot.db.reactions.create_reaction_user(
                clean, message.id, user.id
            )

    await starboard_funcs.update_message(bot, message.id, message.guild.id)


async def scan_recount(
    bot: Bot, channel: discord.TextChannel, limit: int
) -> None:
    starboards = await bot.db.starboards.get_many(channel.guild.id)
    sbemojis = [e for s in starboards for e in s["star_emojis"]]

    async for message in channel.history(limit=limit):
        if not needs_recount(message, sbemojis, min_reactions=2):
            continue
        orig = await starboard_funcs.orig_message(bot, message.id)
        if not orig:
            await bot.db.messages.create(
                message.id,
                message.guild.id,
                message.channel.id,
                message.author.id,
                message.channel.is_nsfw(),
            )
        else:
            message = await bot.cache.fetch_message(
                message.guild.id, int(orig["channel_id"]), int(orig["id"])
            )
        await recount_reactions(bot, message, sbemojis=sbemojis)
