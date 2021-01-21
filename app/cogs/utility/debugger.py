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
    sql_starboards = await bot.db.get_starboards(guild.id)
    starboards = [guild.get_channel(int(s["id"])) for s in sql_starboards]
    if len(sql_starboards) == 0:
        result["warns"].append("You have no starboards set.")
    else:
        for x, s in enumerate(sql_starboards):
            obj = starboards[x]
            if obj is None:
                result["warns"].append(
                    f"A starboard was deleted from this server, "
                    "but not from the database. Run `sb!s remove "
                    f"{s['id']}` to remove it."
                )
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

    # Suggestions
    sql_guild = await bot.db.get_guild(guild.id)
    if not sql_guild["log_channel"]:
        result["suggestions"].append(
            "Add a logChannel (`sb!logChannel <channel>`), where I will "
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
