from typing import List

import discord

from app.classes.bot import Bot


async def debug_guild(bot: Bot, guild: discord.Guild) -> dict:
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
            f"Missing `Send Messages` in {len(missing_send_messages)}/"
            f"{total_channels} channels."
        )
    if len(missing_embed_links) > 0:
        result["warns"].append(
            f"Missing `Embed Links` in {len(missing_embed_links)}/"
            f"{total_channels} channels."
        )
    if len(missing_read_messages) > 0:
        result["warns"].append(
            f"Missing `Read Messages` in {len(missing_read_messages)}/"
            f"{total_channels} channels."
        )
    if len(missing_read_history) > 0:
        result["warns"].append(
            f"Missing `Read Message History` in {len(missing_read_messages)}/"
            f"{total_channels} channels."
        )

    # Check starboard
    sql_starboards = await bot.db.starboards.get_starboards(guild.id)
    starboards = [guild.get_channel(int(s["id"])) for s in sql_starboards]
    if len(sql_starboards) == 0:
        result["warns"].append("You have no starboards set.")
    else:
        if None in starboards:
            result["warns"].append(
                "There are some starboards where the original "
                "channel was deleted. This can be resolved by "
                "running the `clean` command."
            )
        for x, s in enumerate(sql_starboards):
            obj = starboards[x]
            if obj is None:
                continue
            if len(s["star_emojis"]) == 0:
                result["errors"].append(
                    f"The starboard <#{s['id']}> has no starEmojis set, "
                    "so it can't be used."
                )
            if s["self_star"] is False:
                result["light_warns"].append(
                    f"selfStar is disabled for {obj.mention}, so "
                    "users can't star their own messages."
                )
            if s["regex"]:
                result["light_warns"].append(
                    f"{obj.mention} has a regex string, `{s['regex']}`, "
                    "so all messages must match that regex or they can't "
                    "be starred."
                )
            if s["exclude_regex"]:
                result["light_warns"].append(
                    f"{obj.mention} has an excludeRegex string, "
                    f"`{s['exclude_regex']}`, so all messages must "
                    "**not** match this regex or they can't be starred."
                )

            perms = obj.permissions_for(guild.me)
            if not perms.send_messages:
                result["errors"].append(
                    f"I can't send messages in {obj.mention}"
                )
            if not perms.embed_links:
                result["errors"].append(
                    f"I don't have the `Embed Links` permission in "
                    f"{obj.mention}, so I can't send starboard messages."
                )
            if not perms.read_messages:
                result["errors"].append(
                    f"I don't have the `Read Messages` permission in "
                    f"{obj.mention}, so I can't update starboard messages."
                )
            if not perms.read_message_history:
                result["errors"].append(
                    f"I don't have the `Read Message History` permission in "
                    f"{obj.mention}, so I can't update starboard messages."
                )
            if not perms.add_reactions:
                result["errors"].append(
                    f"I don't have the `Add Reactions` permission in "
                    f"{obj.mention}, so I can't autoreact to starboard "
                    "messages there."
                )

    # Check AutoStarChannels
    sql_aschannels = await bot.db.aschannels.get_aschannels(guild.id)
    aschannels = [guild.get_channel(int(asc["id"])) for asc in sql_aschannels]
    if None in aschannels:
        result["warns"].append(
            "There are some AutoStarChannels where the original channel "
            "was deleted. This can be resolved by running the `clean` "
            "command."
        )
    for x, asc in enumerate(sql_aschannels):
        obj = aschannels[x]
        if obj is None:
            continue
        if len(asc["emojis"]) == 0:
            result["light_warns"].append(
                f"The AutoStarChannel {obj.mention} has no emojis set. "
                "This means that none of the messages there will receive "
                "any reactions automatically."
            )
        if not asc["delete_invalid"]:
            # Only check setting is deleteInvalid is False, because if it
            # is True then it will be clear why messages are being deleted.
            if asc["min_chars"] != 0:
                result["light_warns"].append(
                    f"The AutoStarChannel {obj.mention} has minChars set to "
                    f"{asc['min_chars']}, so messages less than that will be "
                    "ignored."
                )
            if asc["require_image"]:
                result["light_warns"].append(
                    f"The AutoStarChannel {obj.mention} has requireImage "
                    "enabled, so all messages must include an image or "
                    "they will be ignored."
                )
            if asc["regex"]:
                result["light_warns"].append(
                    f"The AutoStarChannel {obj.mention} has a regex string "
                    f"(`{asc['regex']}`) that all messages must match or "
                    "they will be ignored."
                )
            if asc["exclude_regex"]:
                result["light_warns"].append(
                    f"The AutoStarChannel {obj.mention} has a regex string "
                    f"(`{asc['exclude_regex']}`) that all messages must not "
                    "match or they will be ignored."
                )

        perms = obj.permissions_for(guild.me)
        if not perms.read_messages:
            result["errors"].append(
                f"I'm missing the `Read Messages` permission in {obj.mention}"
                ", which is an AutoStarChannel. Without this permission, I "
                "won't be able to autoreact to messages there."
            )
        if not perms.add_reactions:
            result["errors"].append(
                f"I'm missing the `Add Reactions` permission in {obj.mention}"
                ", which is an AutoStarChannel. Without this permision, I "
                "won't be able to autoreact to messages there."
            )
        if not perms.manage_messages and asc["delete_invalid"]:
            result["errors"].append(
                f"I'm missing the `Manage Messages` permission in "
                f"{obj.mention}, which is an AutoStarChannel. Without that "
                "permission, I won't be able to delete messages that don't "
                "meet the requirements."
            )

    # Suggestions
    sql_guild = await bot.db.guilds.get_guild(guild.id)
    if not sql_guild["log_channel"]:
        result["suggestions"].append(
            "Add a logChannel (`logChannel <channel>`), where I will "
            "send important information and errors."
        )
    else:
        log_channel = guild.get_channel(sql_guild["log_channel"])
        if not log_channel:
            result["errors"].append(
                "The log channel was deleted, please create a new one."
            )
        else:
            perms = log_channel.permissions_for(guild.me)
            if not perms.send_messages:
                result["errors"].append(
                    f"I can't send messages in {log_channel.mention}, "
                    "so I can't log errors."
                )
            if not perms.embed_links:
                result["errors"].append(
                    "I'm missing the `Embed Links` permission in "
                    f"{log_channel.mention}, so I can't log errors."
                )

    return result
