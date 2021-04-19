import asyncio
from typing import Optional

import discord

from app import gifs, utils
from app.classes.bot import Bot
from app.cogs.permroles import pr_functions
from app.i18n import t_

ZERO_WIDTH_SPACE = "\u200B"


async def can_add(
    bot: Bot,
    emoji: str,
    guild_id: int,
    member: discord.Member,
    channel_id: int,
    sql_author: dict,
    author_roles: list[int],
) -> tuple[bool, bool]:
    """Whether or not a user has permission to add a reaction,
    and returns two values:

    can_add: Whether or not the reaction will count as a point on any of
        the starboards
    remove: Whether or not the bot should automatically remove it
    """

    if member.bot:
        return False, False  # Completely ignore bot reactions

    # First check if the emoji is a starEmoji on any of the starboards
    _starboards = await bot.db.fetch(
        """SELECT * FROM starboards
        WHERE guild_id=$1
        AND $2=any(star_emojis)""",
        guild_id,
        emoji,
    )
    starboards: list[dict] = []
    for s in _starboards:
        if s["channel_wl"]:
            if channel_id not in [int(cid) for cid in s["channel_wl"]]:
                continue
        elif s["channel_bl"]:
            if channel_id not in [int(cid) for cid in s["channel_bl"]]:
                continue
        starboards.append(s)
    if len(starboards) == 0:
        return False, False

    # Next, check if the reaction is valid or invalid. Can be invalid because:
    #   It's a selfStar
    #   The user is missing the proper permissions
    #   The channel is blacklisted
    # In order for it to be invalid, the emoji needs to be invalid on *all*
    # starboards that use this emoji. If any of the starboards consider
    # it valid, then it cannot be automatically removed or ignored.

    # Start by assuming invalid
    valid = False
    remove = True

    current_valid: Optional[bool] = None
    for s in starboards:
        if not s["remove_invalid"]:
            remove = False
        if current_valid is not None:
            if current_valid:
                valid = True
                break

        current_valid = True

        # Check selfStar
        if not s["self_star"] and member.id == int(sql_author["id"]):
            current_valid = False
            continue

        # Check bots
        if (not s["allow_bots"]) and sql_author["is_bot"]:
            current_valid = False
            continue

        # Check the perms of the star giver
        giver_perms = await pr_functions.get_perms(
            bot,
            [r.id for r in member.roles],
            guild_id,
            channel_id,
            int(s["id"]),
        )
        if not giver_perms["give_stars"]:
            current_valid = False
            continue

        # Check the perms of the star receiver
        recv_perms = await pr_functions.get_perms(
            bot, author_roles, guild_id, channel_id, int(s["id"])
        )
        if not recv_perms["on_starboard"]:
            current_valid = False
            continue

    if current_valid:
        valid = True

    return valid, (not valid) and remove


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


async def get_or_set_webhook(
    bot: Bot, starboard: discord.TextChannel
) -> Optional[discord.Webhook]:
    sql_starboard = await bot.db.starboards.get(starboard.id)
    webhook = None
    if sql_starboard["webhook_url"]:
        webhook = bot.get_webhook(sql_starboard["webhook_url"])

    if webhook:
        return webhook

    try:
        webhook = await starboard.create_webhook(
            name=bot.user.name,
            reason=t_("Creating webhook for starboard messages."),
        )
    except discord.Forbidden:
        return None
    await bot.db.starboards.set_webhook(starboard.id, webhook.url)
    return webhook


async def sbemojis(bot: Bot, guild_id: int) -> list[str]:
    return await bot.db.starboards.star_emojis(guild_id)


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
                content += f"{utils.escmd(embed.footer.text)}"
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
                gif_url = await gifs.get_gif_url(bot, embed.url)
                urls.append(
                    {
                        "name": "GIF",
                        "display_url": gif_url or embed.thumbnail.url,
                        "url": embed.url,
                        "type": "gif",
                        "spoiler": False,
                        "show_link": True,
                        "thumbnail_only": False,
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
    if message.reference is not None and bot.get_guild(
        message.reference.guild_id
    ):
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

    guild = bot.get_guild(guild_id)
    await bot.set_locale(guild)

    if not sql_message:
        return
    sql_starboards = await bot.db.starboards.get_many(guild_id)
    sql_author = await bot.db.users.get(sql_message["author_id"])
    all_tasks = []
    if not sql_message["trashed"]:
        for s in sql_starboards:
            all_tasks.append(
                asyncio.create_task(
                    handle_starboard(bot, s, sql_message, sql_author, guild)
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


async def calculate_points(
    bot: Bot, message: dict, starboard: dict, guild: discord.Guild
) -> int:
    _reactions = await bot.db.fetch(
        """SELECT * FROM reactions
        WHERE message_id=$1
        AND emoji=any($2::TEXT[])""",
        message["id"],
        starboard["star_emojis"],
    )

    if starboard["self_star"] is False:
        uid = message["author_id"]
    else:
        uid = None

    _reactions = await bot.db.fetch(
        """SELECT * FROM reaction_users
        WHERE reaction_id=any($1::BIGINT[])
        AND ($2::numeric IS NULL OR $2::numeric!=user_id)""",
        [r["id"] for r in _reactions],
        uid,
    )
    users = list(set(int(r["user_id"]) for r in _reactions))
    user_objs = await bot.cache.get_members(users, guild)
    valid = 0
    for uid in users:
        obj = user_objs.get(uid, None)
        if not obj:
            continue
        perms = await pr_functions.get_perms(
            bot,
            [r.id for r in obj.roles],
            guild.id,
            message["channel_id"],
            starboard["id"],
        )
        if not perms["give_stars"]:
            continue
        valid += 1
    return valid


async def handle_trashed_message(
    bot: Bot, sql_starboard: dict, sql_message: dict, sql_author: dict
) -> None:
    webhook = None
    if sql_starboard["webhook_url"]:
        webhook = bot.get_webhook(sql_starboard["webhook_url"])

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
        if starboard_message.author.id == bot.user.id:
            await starboard_message.edit(embed=embed)
        elif webhook and starboard_message.author.id == webhook.id:
            await webhook.edit_message(starboard_message.id, embed=embed)
    except discord.errors.NotFound:
        pass


async def try_regex(
    bot: Bot, pattern: str, message: discord.Message
) -> Optional[bool]:
    string = message.system_content
    jump = message.jump_url
    try:
        if utils.safe_regex(string, pattern):
            return True
    except TimeoutError:
        async with bot.temp_locale(message.guild):
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
    bot: Bot,
    sql_starboard: dict,
    sql_message: dict,
    sql_author: dict,
    guild: discord.Guild,
) -> None:
    starboard: discord.TextChannel = guild.get_channel(
        int(sql_starboard["id"])
    )

    webhook = None
    if sql_starboard["use_webhook"]:
        webhook = await get_or_set_webhook(bot, starboard)
    elif sql_starboard["webhook_url"]:
        webhook = bot.get_webhook(sql_starboard["webhook_url"])

    sql_starboard_message = await bot.db.fetchrow(
        """SELECT * FROM starboard_messages
        WHERE orig_id=$1 AND starboard_id=$2""",
        sql_message["id"],
        sql_starboard["id"],
    )
    if not sql_message["frozen"] or sql_starboard_message is None:
        points = await calculate_points(bot, sql_message, sql_starboard, guild)
    else:
        points = sql_starboard_message["points"]
    if sql_starboard_message is not None:
        await set_points(bot, points, sql_starboard_message["id"])

    try:
        message = await bot.cache.fetch_message(
            int(sql_message["guild_id"]),
            int(sql_message["channel_id"]),
            int(sql_message["id"]),
        )
    except discord.Forbidden:
        return

    blacklisted = sql_message["channel_id"] in sql_starboard["channel_bl"]
    whitelisted = sql_message["channel_id"] in sql_starboard["channel_wl"]
    if whitelisted:
        blacklisted = False

    _author = await bot.cache.get_members(
        [int(sql_message["author_id"])], guild
    )
    if _author:
        author = _author[int(sql_message["author_id"])]
        roles = [r.id for r in author.roles]
    else:
        roles = []

    user_perms = await pr_functions.get_perms(
        bot, roles, guild.id, sql_message["channel_id"], starboard.id
    )

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
            if await try_regex(bot, sql_starboard["regex"], message) is False:
                add = False
                delete = True
        if sql_starboard["exclude_regex"] != "":
            if (
                await try_regex(bot, sql_starboard["exclude_regex"], message)
                is True
            ):
                add = False
                delete = True

    if sql_message["frozen"]:
        add = False
        delete = False

    if not user_perms["on_starboard"]:
        add = False
        delete = True

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
        if starboard_message.author.id == bot.user.id:
            try:
                await starboard_message.delete()
            except discord.errors.NotFound:
                pass
        elif webhook and starboard_message.author.id == webhook.id:
            try:
                await webhook.delete_message(starboard_message.id)
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
                if not webhook or not sql_starboard["use_webhook"]:
                    m = await starboard.send(
                        plain_text,
                        embed=embed,
                        files=attachments,
                        allowed_mentions=discord.AllowedMentions(users=True),
                    )
                else:
                    try:
                        m = await webhook.send(
                            content=plain_text,
                            embed=embed,
                            files=attachments,
                            allowed_mentions=discord.AllowedMentions(
                                users=True
                            ),
                            wait=True,
                            username=sql_starboard["webhook_name"]
                            or guild.me.display_name,
                            avatar_url=sql_starboard["webhook_avatar"]
                            or bot.user.avatar_url,
                        )
                    except discord.NotFound:
                        await bot.db.starboards.set_webhook(starboard.id, None)
                        return await handle_starboard(
                            bot, sql_starboard, sql_message, sql_author, guild
                        )
            except discord.Forbidden:
                async with bot.temp_locale(guild):
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
                        _m = starboard.get_partial_message(m.id)
                        await _m.add_reaction(emoji)
                    except discord.Forbidden:
                        async with bot.temp_locale(guild):
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
                    if starboard_message.author.id == bot.user.id:
                        await starboard_message.edit(
                            content=plain_text, embed=embed
                        )
                    elif webhook and starboard_message.author.id == webhook.id:
                        await webhook.edit_message(
                            starboard_message.id,
                            content=plain_text,
                            embed=embed,
                        )
                else:
                    if starboard_message.author.id == bot.user.id:
                        await starboard_message.edit(content=plain_text)
                    elif webhook and starboard_message.author.id == webhook.id:
                        await webhook.edit_message(
                            starboard_message.id, content=plain_text
                        )
            except discord.errors.NotFound:
                pass
        elif starboard_message is not None:
            try:
                if starboard_message.author.id == bot.user.id:
                    await starboard_message.edit(content=plain_text)
                elif webhook and starboard_message.author.id == webhook.id:
                    await webhook.edit_message(
                        starboard_message.id, content=plain_text
                    )
            except discord.errors.NotFound:
                pass
