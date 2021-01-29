import discord

from app.classes.bot import Bot
from app import utils
from app.cogs.starboard import starboard_funcs


async def recount_reactions(
    bot: Bot, message: discord.Message, min: int = 0
) -> None:
    starboards = await bot.db.starboards.get_many(message.guild.id)
    sbemojis = [e for s in starboards for e in s["star_emojis"]]

    for reaction in message.reactions:
        clean = utils.clean_emoji(reaction)
        if clean not in sbemojis:
            continue
        if reaction.count <= min:
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
    async for message in channel.history(limit=limit):
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
        await recount_reactions(bot, message, min=2)
