from typing import Any, Dict, List

import discord

from app.classes.bot import Bot
from app.i18n import t_


async def debug_guild(bot: Bot, guild: discord.Guild) -> Dict[Any, Any]:
    result = {
        "light_warns": [],
        "warns": [],
        "errors": [],
        "suggestions": [],
        "missing_channel_perms": {
            "send_messages": [],
            "embed_links": [],
            "read_messages": [],
            "read_history": [],
        },
    }

    # Check channel perms
    total_channels = len(guild.text_channels)
    missing_send_messages: List[discord.TextChannel] = []
    missing_embed_links: List[discord.TextChannel] = []
    missing_read_messages: List[discord.TextChannel] = []
    missing_read_history: List[discord.TextChannel] = []
    for c in guild.text_channels:
        perms = c.permissions_for(guild.me)
        if not perms.send_messages:
            missing_send_messages.append(c)
        if not perms.embed_links:
            missing_embed_links.append(c)
        if not perms.read_messages:
            missing_read_messages.append(c)
        if not perms.read_message_history:
            missing_read_history.append(c)

    if len(missing_send_messages) > 0:
        result["warns"].append(
            t_("Missing `Send Messages` in {0}/{1} channels.").format(
                len(missing_send_messages), total_channels
            )
        )
    if len(missing_embed_links) > 0:
        result["warns"].append(
            t_("Missing `Embed Links` in {0}/{1} channels.").format(
                len(missing_embed_links), total_channels
            )
        )
    if len(missing_read_messages) > 0:
        result["warns"].append(
            t_("Missing `View Channel` in {0}/{1} channels.").format(
                len(missing_read_messages), total_channels
            )
        )
    if len(missing_read_history) > 0:
        result["warns"].append(
            t_("Missing `Read Message History` in {0}/{1} channels.").format(
                len(missing_read_history), total_channels
            )
        )

    # Check starboard
    sql_starboards = await bot.db.starboards.get_many(guild.id)
    starboards = [guild.get_channel(int(s["id"])) for s in sql_starboards]
    if len(sql_starboards) == 0:
        result["warns"].append(t_("You have no starboards set."))
    else:
        if None in starboards:
            result["warns"].append(
                t_(
                    "There are some starboards where the original "
                    "channel was deleted. This can be resolved by "
                    "running the `clean` command."
                )
            )
        for x, s in enumerate(sql_starboards):
            obj = starboards[x]
            if obj is None:
                continue
            if len(s["star_emojis"]) == 0:
                result["errors"].append(
                    t_(
                        "The starboard <#{0}> has no starEmojis set, "
                        "so it can't be used."
                    ).format(s["id"])
                )
            if s["self_star"] is False:
                result["light_warns"].append(
                    t_(
                        "selfStar is disabled for {0}, so "
                        "users can't star their own messages."
                    ).format(obj.mention)
                )
            if s["regex"]:
                result["light_warns"].append(
                    t_(
                        "{0} has a regex string, `{1}`, "
                        "so all messages must match that regex or they can't "
                        "be starred."
                    ).format(obj.mention, s["regex"])
                )
            if s["exclude_regex"]:
                result["light_warns"].append(
                    t_(
                        "{0} has an excludeRegex string, "
                        "`{1}`, so all messages must "
                        "**not** match this regex or they can't be starred."
                    ).format(obj.mention, s["exclude_regex"])
                )

            perms = obj.permissions_for(guild.me)
            if not perms.send_messages:
                result["errors"].append(
                    t_("I can't send messages in {0}.").format(obj.mention)
                )
            if not perms.embed_links:
                result["errors"].append(
                    t_(
                        "I don't have the `Embed Links` permission in "
                        "{0}, so I can't send starboard messages."
                    ).format(obj.mention)
                )
            if not perms.read_messages:
                result["errors"].append(
                    t_(
                        "I don't have the `View Channel` permission in "
                        "{0}, so I can't update starboard messages."
                    ).format(obj.mention)
                )
            if not perms.read_message_history:
                result["errors"].append(
                    t_(
                        "I don't have the `Read Message History` permission "
                        "in {0}, so I can't update starboard messages."
                    ).format(obj.mention)
                )
            if not perms.add_reactions:
                result["errors"].append(
                    t_(
                        "I don't have the `Add Reactions` permission in "
                        "{0}, so I can't autoreact to starboard "
                        "messages there."
                    ).format(obj.mention)
                )

            # Check channel blacklisting/whitelisting
            blacklisted = len(s["channel_bl"])
            whitelisted = len(s["channel_wl"])

            if blacklisted != 0 and whitelisted == 0:
                result["light_warns"].append(
                    t_(
                        "<#{0}> has {1} blacklisted channels, "
                        "so messages from those channels can't be starred."
                    ).format(s["id"], blacklisted)
                )
            if whitelisted != 0:
                result["light_warns"].append(
                    t_(
                        "<#{0}> has {1} whitelisted channels, "
                        "so only messages from those channels can be starred."
                    ).format(s["id"], whitelisted)
                )

    # Check AutoStar channels
    sql_aschannels = await bot.db.aschannels.get_many(guild.id)
    aschannels = [guild.get_channel(int(asc["id"])) for asc in sql_aschannels]
    if None in aschannels:
        result["warns"].append(
            t_(
                "There are some AutoStar channels where the original channel "
                "was deleted. This can be resolved by running the `clean` "
                "command."
            )
        )
    for x, asc in enumerate(sql_aschannels):
        obj = aschannels[x]
        if obj is None:
            continue
        if len(asc["emojis"]) == 0:
            result["light_warns"].append(
                t_(
                    "The AutoStar channel {0} has no emojis set. "
                    "This means that none of the messages there will receive "
                    "any reactions automatically."
                ).format(obj.mention)
            )
        if not asc["delete_invalid"]:
            # Only check setting is deleteInvalid is False, because if it
            # is True then it will be clear why messages are being deleted.
            if asc["min_chars"] != 0:
                result["light_warns"].append(
                    t_(
                        "The AutoStar channel {0} has minChars set to "
                        "{asc['min_chars']}, so messages less than that will "
                        "be ignored."
                    ).format(obj.mention)
                )
            if asc["require_image"]:
                result["light_warns"].append(
                    t_(
                        "The AutoStar channel {0} has requireImage "
                        "enabled, so all messages must include an image or "
                        "they will be ignored."
                    ).format(obj.mention)
                )
            if asc["regex"]:
                result["light_warns"].append(
                    t_(
                        "The AutoStar channel {0} has a regex string "
                        "(`{1}`) that all messages must match or "
                        "they will be ignored."
                    ).format(obj.mention, asc["regex"])
                )
            if asc["exclude_regex"]:
                result["light_warns"].append(
                    t_(
                        "The AutoStar channel {0} has a regex string "
                        "(`{1}`) that all messages must not "
                        "match or they will be ignored."
                    ).format(obj.mention, asc["exclude_regex"])
                )

        perms = obj.permissions_for(guild.me)
        if not perms.read_messages:
            result["errors"].append(
                t_(
                    "I'm missing the `View Channel` permission in {0}"
                    ", which is an AutoStar channel. Without this "
                    "permission, I won't be able to autoreact to "
                    "messages there."
                ).format(obj.mention)
            )
        if not perms.add_reactions:
            result["errors"].append(
                t_(
                    "I'm missing the `Add Reactions` permission in {0}"
                    ", which is an AutoStar channel. Without this "
                    "permision, I won't be able to autoreact to messages "
                    "there."
                ).format(obj.mention)
            )
        if not perms.manage_messages and asc["delete_invalid"]:
            result["errors"].append(
                t_(
                    "I'm missing the `Manage Messages` permission in "
                    "{0}, which is an AutoStar channel. Without that "
                    "permission, I won't be able to delete messages "
                    "that don't meet the requirements."
                ).format(obj.mention)
            )

    # Suggestions
    sql_guild = await bot.db.guilds.get(guild.id)
    if not sql_guild["log_channel"]:
        result["suggestions"].append(
            t_(
                "Add a logChannel (`logChannel <channel>`), where I will "
                "send important information and errors."
            )
        )
    else:
        log_channel = guild.get_channel(sql_guild["log_channel"])
        if not log_channel:
            result["errors"].append(
                t_("The log channel was deleted, please create a new one.")
            )
        else:
            perms = log_channel.permissions_for(guild.me)
            if not perms.send_messages:
                result["errors"].append(
                    t_(
                        "I can't send messages in {0}, so I can't log errors."
                    ).format(log_channel.mention)
                )
            if not perms.embed_links:
                result["errors"].append(
                    t_(
                        "I'm missing the `Embed Links` permission in "
                        "{0}, so I can't log errors."
                    ).format(log_channel.mention)
                )

    return result
