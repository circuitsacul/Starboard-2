import asyncio
from typing import Optional

import discord

from app import utils
from app.i18n import t_
from app.classes.bot import Bot

ZERO_WIDTH_SPACE = "\u200B"


def get_plain_text(
    starboard: dict, orig_message: dict, points: int, guild: discord.Guild
) -> str:
    forced = starboard["id"] in orig_message["forced"]
    frozen = orig_message["frozen"]
    emoji = utils.pretty_emoji_string([starboard["display_emoji"]], guild)
    channel = f"<#{orig_message['channel_id']}>"
    mention = starboard["ping"]
    return str(
        f"**{emoji} {points} | {channel}"
        + (f" | <@{orig_message['author_id']}>" if mention else "")
        + f"{' 🔒' if forced else ''}{' ❄️' if frozen else ''}**"
    )


async def sbemojis(bot: Bot, guild_id: int) -> list[str]:
    _emojis = await bot.db.fetch(
        """SELECT star_emojis FROM starboards
        WHERE guild_id=$1""",
        guild_id,
    )
    if _emojis:
        emojis = [
            emoji for record in _emojis for emoji in record["star_emojis"]
        ]
    else:
        emojis = []
    return emojis


async def orig_message(bot: Bot, message_id: int) -> Optional[dict]:
    starboard_message = await bot.db.sb_messages.get(message_id)

    if starboard_message is not None:
        return await bot.db.messages.get(starboard_message["orig_id"])

    return await bot.db.messages.get(message_id)


async def embed_message(
    bot: Bot, message: discord.Message, color: str = None, files: bool = True
) -> tuple[discord.Embed, list[discord.File]]:
    nsfw = message.channel.is_nsfw()
    content = utils.escmask(message.system_content)

    urls = []
    extra_attachments = []
    image_used = False
    thumbnail_used = False

    for attachment in message.attachments:
        if files:
            try:
                f = await attachment.to_file()
            except (discord.Forbidden, discord.HTTPException):
                f = None
        else:
            f = None
        urls.append(
            {
                "name": attachment.filename,
                "display_url": attachment.url,
                "url": attachment.url,
                "type": "upload",
                "spoiler": attachment.is_spoiler(),
                "file": f,
                "show_link": True,
                "thumbnail_only": False,
            }
        )

    embed: discord.Embed
    for embed in message.embeds:
        if embed.type in ["rich", "article", "link"]:
            if embed.title != embed.Empty:
                if embed.url == embed.Empty:
                    content += f"\n\n__**{utils.escmd(embed.title)}**__\n"
                else:
                    content += (
                        f"\n\n__**[{utils.escmd(embed.title)}]({embed.url})"
                        "**__\n"
                    )
            else:
                content += "\n"
            content += (
                (f"{embed.description}\n")
                if embed.description != embed.Empty
                else ""
            )

            for field in embed.fields:
                name = f"\n**{utils.escmd(field.name)}**\n"
                value = f"{field.value}\n"

                content += name + value
            if embed.footer.text is not embed.Empty:
                content += f"\n{utils.escmd(embed.footer.text)}\n"
            if embed.image.url is not embed.Empty:
                urls.append(
                    {
                        "name": "Embed Image",
                        "url": embed.image.url,
                        "display_url": embed.image.url,
                        "type": "image",
                        "spoiler": False,
                        "show_link": False,
                        "thumbnail_only": False,
                    }
                )
            if embed.thumbnail.url is not embed.Empty:
                urls.append(
                    {
                        "name": "Embed Thumbnail",
                        "url": embed.thumbnail.url,
                        "display_url": embed.thumbnail.url,
                        "type": "image",
                        "spoiler": False,
                        "show_link": False,
                        "thumbnail_only": True,
                    }
                )
        elif embed.type == "image":
            if embed.url is not embed.Empty:
                urls.append(
                    {
                        "name": "Image",
                        "display_url": embed.thumbnail.url,
                        "url": embed.url,
                        "type": "image",
                        "spoiler": False,
                        "show_link": True,
                        "thumbnail_only": False,
                    }
                )
        elif embed.type == "gifv":
            if embed.url is not embed.Empty:
                urls.append(
                    {
                        "name": "GIF",
                        "display_url": embed.thumbnail.url,
                        "url": embed.url,
                        "type": "gif",
                        "spoiler": False,
                        "show_link": True,
                        "thumbnail_only": True,
                    }
                )
        elif embed.type == "video":
            if embed.url is not embed.Empty:
                urls.append(
                    {
                        "name": embed.title,
                        "display_url": embed.thumbnail.url,
                        "url": embed.url,
                        "type": "video",
                        "spoiler": False,
                        "show_link": True,
                        "thumbnail_only": False,
                    }
                )

    if len(content) > 2048:
        to_remove = len(content + " ...") - 2048
        content = content[:-to_remove]

    embed = discord.Embed(
        color=bot.theme_color
        if color is None
        else int(color.replace("#", ""), 16),
        description=content,
    ).set_author(name=str(message.author), icon_url=message.author.avatar_url)

    ref_message = None
    ref_jump = None
    ref_author = None
    if message.reference is not None:
        if message.reference.resolved is None:
            ref_message = await bot.cache.fetch_message(
                message.reference.guild_id,
                message.reference.channel_id,
                message.reference.message_id,
            )
            if ref_message is None:
                ref_content = t_("*Message was deleted*")
            else:
                ref_author = str(ref_message.author)
                ref_content = ref_message.system_content
        else:
            ref_message = message.reference.resolved
            if type(message.reference.resolved) is discord.Message:
                ref_content = message.reference.resolved.system_content
                ref_author = str(ref_message.author)
            else:
                ref_content = t_("*Message was deleted*")

        if ref_content == "":
            ref_content = t_("*File Only*")

        embed.add_field(
            name=f'Replying to {ref_author or t_("Unknown")}',
            value=ref_content,
            inline=False,
        )

        if type(ref_message) is discord.Message:
            ref_jump = t_("**[Replying to {0}]({1})**\n").format(
                ref_author, ref_message.jump_url
            )
        else:
            ref_jump = t_(
                "**[Replying to Unknown (deleted)]"
                "(https://discord.com/channels/{0.guild_id}/"
                "{0.channel_id}/{0.message_id})**\n"
            ).format(message.reference)

    embed.add_field(
        name=ZERO_WIDTH_SPACE,
        value=str(
            str(ref_jump if ref_message else "")
            + t_("**[Jump to Message]({0})**").format(message.jump_url),
        ),
        inline=False,
    )

    image_types = ["png", "jpg", "jpeg", "gif", "gifv", "svg", "webp"]
    for data in urls:
        if data["type"] == "upload":
            is_image = False
            for t in image_types:
                if data["url"].endswith(t):
                    is_image = True
                    break
            added = False
            if is_image and not nsfw and not data["spoiler"]:
                if not image_used:
                    embed.set_image(url=data["display_url"])
                    image_used = True
                    added = True
            if not added and data["file"] is not None:
                f: discord.File = data["file"]
                if nsfw:
                    f.filename = "SPOILER_" + f.filename
                extra_attachments.append(f)
        elif not nsfw:
            if data["thumbnail_only"]:
                if not thumbnail_used:
                    embed.set_thumbnail(url=data["display_url"])
                    thumbnail_used = True
            elif not image_used:
                embed.set_image(url=data["display_url"])
                image_used = True

    to_show = str(
        "\n".join(
            f"**[{d['name']}]({d['url']})**" for d in urls if d["show_link"]
        )
    )

    if len(to_show) != 0:
        embed.add_field(name=ZERO_WIDTH_SPACE, value=to_show)

    embed.timestamp = message.created_at

    return embed, extra_attachments


async def update_message(bot: Bot, message_id: int, guild_id: int) -> None:
    sql_message = await bot.db.messages.get(message_id)
    if not sql_message:
        return
    sql_starboards = await bot.db.starboards.get_many(guild_id)
    sql_author = await bot.db.users.get(sql_message["author_id"])
    all_tasks = []
    if not sql_message["trashed"]:
        for s in sql_starboards:
            all_tasks.append(
                asyncio.create_task(
                    handle_starboard(bot, s, sql_message, sql_author)
                )
            )
        for t in all_tasks:
            await t
    else:
        for s in sql_starboards:
            await handle_trashed_message(bot, s, sql_message, sql_author)


async def set_points(bot: Bot, points: int, message_id: int) -> None:
    await bot.db.execute(
        """UPDATE starboard_messages
        SET points=$1 WHERE id=$2""",
        points,
        message_id,
    )


async def calculate_points(bot: Bot, message: dict, starboard: dict) -> int:
    _reactions = await bot.db.fetch(
        """SELECT * FROM reactions
        WHERE message_id=$1""",
        message["id"],
    )
    reaction_users = await bot.db.fetch(
        """SELECT * FROM reaction_users
        WHERE reaction_id=any($1::BIGINT[])""",
        [r["id"] for r in _reactions],
    )

    reactions = {}
    for r in _reactions:
        reactions[int(r["id"])] = r["emoji"]

    used_users = set()
    points = 0
    for r in reaction_users:
        if r["user_id"] in used_users:
            continue
        if reactions[int(r["reaction_id"])] not in starboard["star_emojis"]:
            continue
        if starboard["self_star"] is False:
            if r["user_id"] == message["author_id"]:
                continue
        used_users.add(r["user_id"])
        points += 1

    return points


async def handle_trashed_message(
    bot: Bot, sql_starboard: dict, sql_message: dict, sql_author: dict
) -> None:
    sql_starboard_message = await bot.db.fetchrow(
        """SELECT * FROM starboard_messages
        WHERE orig_id=$1 AND starboard_id=$2""",
        sql_message["id"],
        sql_starboard["id"],
    )
    if not sql_starboard_message:
        return
    starboard_message = await bot.cache.fetch_message(
        sql_message["guild_id"],
        sql_starboard_message["starboard_id"],
        sql_starboard_message["id"],
    )
    if starboard_message is None:
        return
    embed = discord.Embed(
        title=t_("Trashed Message"),
        description=t_(
            "This message was trashed by a moderator. To untrash it, "
            "run ```\nuntrash {0}-{1}```\nReason:```\n{2}```"
        ).format(
            sql_message["channel_id"],
            sql_message["id"],
            utils.escmd(sql_message["trash_reason"]),
        ),
    )
    try:
        await starboard_message.edit(embed=embed)
    except discord.errors.NotFound:
        pass


def try_regex(
    bot: Bot, pattern: str, message: discord.Message
) -> Optional[bool]:
    string = message.system_content
    jump = message.jump_url
    try:
        if utils.safe_regex(string, pattern):
            return True
    except TimeoutError:
        bot.dispatch(
            "guild_log",
            t_(
                "I tried to match `{0}` to "
                "[a message]({1}), but it took too long. "
                "Try improving the efficiency of your regex. If "
                "you need help, feel free to join the support server."
            ).format(pattern, jump),
            "error",
            message.guild,
        )
        return None
    return False


async def handle_starboard(
    bot: Bot, sql_starboard: dict, sql_message: dict, sql_author: dict
) -> None:
    guild = bot.get_guild(sql_starboard["guild_id"])
    starboard: discord.TextChannel = guild.get_channel(
        int(sql_starboard["id"])
    )

    sql_starboard_message = await bot.db.fetchrow(
        """SELECT * FROM starboard_messages
        WHERE orig_id=$1 AND starboard_id=$2""",
        sql_message["id"],
        sql_starboard["id"],
    )
    if not sql_message["frozen"] or sql_starboard_message is None:
        points = await calculate_points(bot, sql_message, sql_starboard)
    else:
        points = sql_starboard_message["points"]
    if sql_starboard_message is not None:
        await set_points(bot, points, sql_starboard_message["id"])
    message = await bot.cache.fetch_message(
        int(sql_message["guild_id"]),
        int(sql_message["channel_id"]),
        int(sql_message["id"]),
    )

    blacklisted = sql_message["channel_id"] in sql_starboard["channel_bl"]
    whitelisted = sql_message["channel_id"] in sql_starboard["channel_wl"]
    if whitelisted:
        blacklisted = False

    add = False
    edit = sql_starboard["link_edits"]
    delete = False

    if points >= sql_starboard["required"]:
        add = True
    elif points <= sql_starboard["required_remove"]:
        delete = True

    if (not sql_starboard["allow_bots"]) and sql_author["is_bot"]:
        delete = True
        add = False

    if sql_starboard["link_deletes"] and (message is None):
        delete = True
        add = False

    if blacklisted:
        add = False
        delete = True

    if sql_message["is_nsfw"] and not starboard.is_nsfw() and not whitelisted:
        add = False
        delete = True

    if message is not None:
        if sql_starboard["regex"] != "":
            if try_regex(bot, sql_starboard["regex"], message) is False:
                add = False
                delete = True
        if sql_starboard["exclude_regex"] != "":
            if try_regex(bot, sql_starboard["exclude_regex"], message) is True:
                add = False
                delete = True

    if sql_message["frozen"]:
        add = False
        delete = False

    if sql_starboard["id"] in sql_message["forced"]:
        add = True
        delete = False

    if sql_starboard_message is not None:
        starboard_message = await bot.cache.fetch_message(
            int(sql_message["guild_id"]),
            int(sql_starboard_message["starboard_id"]),
            int(sql_starboard_message["id"]),
        )
        if starboard_message is None:
            await bot.db.sb_messages.delete(sql_starboard_message["id"])
        sql_starboard_message = None
    else:
        starboard_message = None

    if delete and starboard_message is not None:
        await bot.db.sb_messages.delete(starboard_message.id)
        try:
            await starboard_message.delete()
        except discord.errors.NotFound:
            pass
    elif not delete:
        guild = bot.get_guild(int(sql_message["guild_id"]))

        plain_text = get_plain_text(sql_starboard, sql_message, points, guild)

        if starboard_message is None and add and message:
            embed, attachments = await embed_message(
                bot, message, color=sql_starboard["color"]
            )
            # starboard = guild.get_channel(int(sql_starboard["id"]))
            try:
                m = await starboard.send(
                    plain_text,
                    embed=embed,
                    files=attachments,
                    allowed_mentions=discord.AllowedMentions(users=True),
                )
            except discord.Forbidden:
                bot.dispatch(
                    "guild_log",
                    t_(
                        "I tried to send a starboard message to "
                        "{0}, but I'm missing the "
                        "proper permissions. Please make sure I have "
                        "the `Send Messages` permission."
                    ).format(starboard.mention),
                    "error",
                    guild,
                )
                return
            await bot.db.sb_messages.create(
                m.id, message.id, sql_starboard["id"]
            )
            await set_points(bot, points, m.id)
            if sql_starboard["autoreact"] is True:
                for emoji in sql_starboard["star_emojis"]:
                    try:
                        emoji_id = int(emoji)
                    except ValueError:
                        emoji_id = None
                    if emoji_id:
                        emoji = discord.utils.get(guild.emojis, id=emoji_id)
                    try:
                        await m.add_reaction(emoji)
                    except discord.Forbidden:
                        bot.dispatch(
                            "guild_log",
                            t_(
                                "I tried to autoreact to a message on the "
                                "starboard, but I'm missing the proper "
                                "permissions. If you don't want me to "
                                "autoreact to messages, set the AutoReact "
                                "setting to False with `starboards cs "
                                "#{0} --autoReact False`."
                            ).format(starboard.name),
                            "error",
                            guild,
                        )
        elif starboard_message is not None and message:
            try:
                if edit:
                    embed, _ = await embed_message(
                        bot, message, color=sql_starboard["color"], files=False
                    )
                    await starboard_message.edit(
                        content=plain_text, embed=embed
                    )
                else:
                    await starboard_message.edit(content=plain_text)
            except discord.errors.NotFound:
                pass
        elif starboard_message is not None:
            try:
                await starboard_message.edit(content=plain_text)
            except discord.errors.NotFound:
                pass
