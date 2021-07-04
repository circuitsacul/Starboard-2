from typing import TYPE_CHECKING, List, Tuple

import discord

from app import gifs, utils
from app.constants import MAX_EMBED_DESC_LENGTH, MAX_EMBED_FIELD_LENGTH, ZWS
from app.i18n import t_

if TYPE_CHECKING:
    from app.classes.bot import Bot


async def add_jump_links(
    bot: "Bot", message: discord.Message, embed: discord.Embed
):
    ref_message = None
    ref_author = None
    if (
        message.reference is not None
        and message.reference.message_id is not None
        and bot.get_guild(message.reference.guild_id)
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
            if isinstance(message.reference.resolved, discord.Message):
                ref_content = message.reference.resolved.system_content
                ref_author = str(ref_message.author)
            else:
                ref_content = t_("*Message was deleted*")

        if ref_content == "":
            ref_content = t_("*File Only*")

        embed.add_field(
            name=f'Replying to {ref_author or t_("Unknown")}',
            value=utils.truncate(ref_content, MAX_EMBED_FIELD_LENGTH),
            inline=False,
        )

    embed.add_field(
        name=ZWS,
        value=t_("**[Jump to Message]({0})**").format(message.jump_url),
        inline=False,
    )


async def extract_embeds(bot: "Bot", message: discord.Message, urls) -> str:
    content = ""
    embed: discord.Embed
    for embed in message.embeds:
        if embed.type in ["rich", "article", "link"]:
            if embed.title != embed.Empty:
                if embed.url == embed.Empty:
                    content += f"\n\n__**{embed.title}**__\n"
                else:
                    content += f"\n\n__**[{embed.title}]({embed.url})**__\n"
            else:
                content += "\n"
            content += (
                (f"{embed.description}\n")
                if embed.description != embed.Empty
                else ""
            )

            for field in embed.fields:
                name = f"\n**{field.name}**\n"
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
                        "show_link": True,
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
                        "show_link": True,
                        "thumbnail_only": embed.type != "article",
                    }
                )

        elif embed.url is not embed.Empty:
            new_url = {
                "display_url": embed.thumbnail.url,
                "url": embed.url,
                "type": "gif" if embed.type == "gifv" else embed.type,
                "spoiler": False,
                "show_link": True,
                "thumbnail_only": False,
            }
            if embed.type == "image":
                new_url = {"name": "Image", **new_url}
            elif embed.type == "gifv":
                gif_url = await gifs.get_gif_url(bot, embed.url)
                new_url = {"name": "GIF", **new_url}
                if gif_url:
                    new_url["display_url"] = gif_url
            elif embed.type == "video":
                new_url = {"name": embed.title, **new_url}

            urls.append(new_url)
    return content


async def extract_attachments(message: discord.Message, files: bool, urls):
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


async def embed_message(
    bot: "Bot",
    message: discord.Message,
    color: str = None,
    nicknames: bool = False,
    files: bool = True,
) -> Tuple[discord.Embed, List[discord.File]]:
    nsfw = message.channel.is_nsfw()
    content = utils.escmask(utils.escesc(message.system_content))

    urls = []
    extra_attachments = []
    image_used = False
    thumbnail_used = False

    await extract_attachments(message, files, urls)
    content += await extract_embeds(bot, message, urls)
    content = utils.truncate(content, MAX_EMBED_DESC_LENGTH)

    _a = message.author
    author_name = (
        f"{_a.display_name}" if nicknames else f"{_a.name}#{_a.discriminator}"
    )

    embed = discord.Embed(
        color=bot.theme_color
        if color is None
        else int(color.replace("#", ""), 16),
        description=content,
    ).set_author(name=author_name, icon_url=message.author.avatar_url)

    await add_jump_links(bot, message, embed)

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

    to_show = ""
    left = len(urls)
    for d in urls:
        and_others_str = t_("{0} additional attachments.").format(left)
        left -= 1
        if not d["show_link"]:
            continue
        newline = True
        if d is urls[0]:
            newline = False
        to_add = f"**[{d['name']}]({d['url']})**"
        if (
            len("\n" if newline else "")
            + len(to_show)
            + len(to_add)
            + len(and_others_str)
            > MAX_EMBED_FIELD_LENGTH
        ):
            to_show += and_others_str
            break
        to_show += ("\n" if newline else "") + to_add

    if len(to_show) != 0:
        embed.add_field(name=ZWS, value=to_show)

    embed.timestamp = message.created_at

    return embed, extra_attachments
