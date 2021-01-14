import time
from typing import Optional, Tuple, List

import discord

from app import utils
from app.classes.bot import Bot


EMPTY = discord.embeds._EmptyEmbed
ZERO_WIDTH_SPACE = "\u200B"


def escmd(text: str) -> str:
    if type(text) is not str:
        return
    return discord.utils.escape_markdown(text)


async def orig_message(
    bot: Bot,
    message_id: int
) -> Optional[dict]:
    starboard_message = await bot.db.get_starboard_message(
        message_id
    )

    if starboard_message is not None:
        return await bot.db.get_message(
            starboard_message['orig_id']
        )

    return await bot.db.get_message(
        message_id
    )


async def embed_message(
    bot: Bot, message: discord.Message
) -> Tuple[discord.Embed, List[discord.File]]:
    content = message.system_content

    embed: discord.Embed
    for embed in message.embeds:
        if embed.type == 'rich':
            content += (
                f"\n__**{escmd(embed.title)}**__\n"
            ) if embed.title != EMPTY else ''
            content += (
                f"{embed.description}\n"
            ) if embed.description != EMPTY else ''

            for field in embed.fields:
                name = f"\n**{escmd(field.name)}**\n" \
                    if field.name != EMPTY else ''
                value = f"{field.value}\n" if field.value != EMPTY else ''

                content += name + value
            if embed.footer.text is not embed.Empty:
                content += f"\n{escmd(embed.footer.text)}\n"

    if len(content) > 2048:
        to_remove = len(content + ' ...') - 2048
        content = content[:-to_remove]

    embed = discord.Embed(
        color=bot.theme_color,
        description=content
    ).set_author(
        name=str(message.author),
        icon_url=message.author.avatar_url
    )

    ref_message = None
    ref_jump = None
    if message.reference is not None:
        if message.reference.resolved is None:
            ref_message = await bot.cache.fetch_message(
                bot, message.guild.id, message.channel.id,
                message.reference.message_id
            )
            if ref_message is None:
                ref_content = "*Message was deleted*"
            else:
                ref_content = ref_message.system_content
        else:
            ref_message = message.reference.resolved
            if type(message.reference.resolved) is discord.Message:
                ref_content = message.reference.resolved.system_content
            else:
                ref_content = "*Message was deleted*"

        if ref_content == '':
            ref_content = '*File Only*'

        embed.add_field(
            name='Replied To',
            value=ref_content,
            inline=False
        )

        if type(ref_message) is discord.Message:
            ref_jump = (
                f"**[Replied to This Message]({ref_message.jump_url})**\n"
            )
        else:
            ref_jump = (
                "**[Replied to This Message (deleted)]"
                f"(https://discord.com/channels/{ref_message.guild_id}/"
                f"{ref_message.channel_id}/{ref_message.id})**\n"
            )

    embed.add_field(
        name=ZERO_WIDTH_SPACE,
        value=str(
            str(ref_jump if ref_message else '') +
            f"**[Jump to Message!]({message.jump_url})**",
        ),
        inline=False
    )

    return embed, []


async def update_message(
    bot: Bot, message_id: int,
    guild_id: int
) -> None:
    sql_message = await bot.db.get_message(
        message_id
    )
    sql_starboards = await bot.db.get_starboards(
        guild_id
    )
    for s in sql_starboards:
        await handle_starboard(bot, s, sql_message)


async def calculate_points(
    bot: Bot, message: dict,
    starboard: dict
) -> int:
    _reactions = await bot.db.fetch(
        """SELECT * FROM reactions
        WHERE message_id=$1""",
        message['id']
    )
    reaction_users = await bot.db.fetch(
        """SELECT * FROM reaction_users
        WHERE reaction_id=any($1::BIGINT[])""",
        [r['id'] for r in _reactions]
    )

    reactions = {}
    for r in _reactions:
        reactions[int(r['id'])] = r['emoji']

    used_users = set()
    points = 0
    for r in reaction_users:
        if r['user_id'] in used_users:
            continue
        if reactions[int(r['reaction_id'])] \
                not in starboard['star_emojis']:
            continue
        used_users.add(r['user_id'])
        points += 1

    return points


async def handle_starboard(
    bot: Bot, sql_starboard: dict,
    sql_message: dict
) -> None:
    points = await calculate_points(
        bot, sql_message, sql_starboard
    )

    add = False
    delete = False

    if points >= sql_starboard['required']:
        add = True
    elif points <= sql_starboard['required_remove']:
        delete = True

    sql_starboard_message = await bot.db.fetchrow(
        """SELECT * FROM starboard_messages
        WHERE orig_id=$1 AND starboard_id=$2""",
        sql_message['id'], sql_starboard['id']
    )

    if sql_starboard_message is not None:
        starboard_message = await bot.cache.fetch_message(
            bot, int(sql_message['guild_id']),
            int(sql_starboard_message['starboard_id']),
            int(sql_starboard_message['id'])
        )
        if starboard_message is None:
            await bot.db.execute(
                """DELETE FROM starboard_messages
                WHERE id=$1""", sql_starboard_message['id']
            )
        sql_starboard_message = None
    else:
        starboard_message = None

    if delete and starboard_message is not None:
        await bot.db.execute(
            """DELETE FROM starboard_messages
            WHERE id=$1""", starboard_message.id
        )
        await starboard_message.delete()
    elif not delete:
        message = await bot.cache.fetch_message(
            bot, int(sql_message['guild_id']),
            int(sql_message['channel_id']),
            int(sql_message['id'])
        )
        embed = None
        if message is not None:
            embed, _ = await embed_message(
                bot, message
            )

        guild = bot.get_guild(int(sql_message['guild_id']))
        display_emoji = utils.pretty_emoji_string(
            sql_starboard['display_emoji'], guild
        )

        plain_text = (
            f"**{display_emoji} {points} | <#{sql_message['channel_id']}>**"
        )

        if starboard_message is None and add and message:
            starboard = bot.get_channel(
                int(sql_starboard['id'])
            )
            m = await starboard.send(plain_text, embed=embed)
            await bot.db.create_starboard_message(
                m.id, message.id, sql_starboard['id']
            )
            if sql_starboard['autoreact'] is True:
                for emoji in sql_starboard['star_emojis']:
                    try:
                        emoji_id = int(emoji)
                    except ValueError:
                        emoji_id = None
                    if emoji_id:
                        emoji = discord.utils.get(guild.emojis, id=emoji_id)
                    await m.add_reaction(emoji)
        elif starboard_message is not None and message:
            start = time.time()
            await starboard_message.edit(
                content=plain_text, embed=embed
            )
            end = time.time()
            print("Edit time:", end-start)
        elif starboard_message is not None:
            start = time.time()
            await starboard_message.edit(
                content=plain_text
            )
            end = time.time()
            print("Edit time:", end-start)
