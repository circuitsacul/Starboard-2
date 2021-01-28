import discord

from app.classes.bot import Bot
from app import utils
from app.cogs.starboard import starboard_funcs


async def recount_reactions(bot: Bot, message: discord.Message) -> None:
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
