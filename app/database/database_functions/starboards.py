from typing import List, Optional

import asyncpg
import discord

from app import errors


class Starboards:
    def __init__(self, bot) -> None:
        self.bot = bot

    async def get(self, starboard_id: int) -> Optional[dict]:
        return await self.bot.db.fetchrow(
            """SELECT * FROM starboards
            WHERE id=$1""",
            starboard_id,
        )

    async def get_many(self, guild_id: int) -> List[dict]:
        return await self.bot.db.fetch(
            """SELECT * FROM starboards
            WHERE guild_id=$1""",
            guild_id,
        )

    async def create(
        self, channel_id: int, guild_id: int, check_first: bool = True
    ) -> bool:
        if check_first:
            exists = await self.get(channel_id) is not None
            if exists:
                return True

        await self.bot.db.guilds.create(guild_id)
        try:
            await self.bot.db.execute(
                """INSERT INTO starboards (id, guild_id)
                VALUES ($1, $2)""",
                channel_id,
                guild_id,
            )
        except asyncpg.exceptions.UniqueViolationError:
            return True
        return False

    async def edit(
        self,
        starboard_id: int = None,
        required: int = None,
        required_remove: int = None,
        autoreact: bool = None,
        self_star: bool = None,
        allow_bots: bool = None,
        allow_nsfw: bool = None,
        link_deletes: bool = None,
        link_edits: bool = None,
        images_only: bool = None,
        remove_reactions: bool = None,
        no_xp: bool = None,
        explore: bool = None,
        star_emojis: List[str] = None,
        display_emoji: str = None,
        ping: bool = None,
        regex: str = None,
        exclude_regex: str = None,
        color: int = None,
    ) -> None:
        s = await self.get(starboard_id)
        if not s:
            raise errors.DoesNotExist(
                f"Starboard {starboard_id} does not exist."
            )

        settings = {
            "required": s["required"] if required is None else required,
            "required_remove": s["required_remove"]
            if required_remove is None
            else required_remove,
            "autoreact": s["autoreact"] if autoreact is None else autoreact,
            "self_star": s["self_star"] if self_star is None else self_star,
            "allow_bots": s["allow_bots"]
            if allow_bots is None
            else allow_bots,
            "allow_nsfw": s["allow_nsfw"]
            if allow_nsfw is None
            else allow_nsfw,
            "link_deletes": s["link_deletes"]
            if link_deletes is None
            else link_deletes,
            "link_edits": s["link_edits"]
            if link_edits is None
            else link_edits,
            "images_only": s["images_only"]
            if images_only is None
            else images_only,
            "remove_reactions": s["remove_reactions"]
            if remove_reactions is None
            else remove_reactions,
            "no_xp": s["no_xp"] if no_xp is None else no_xp,
            "explore": s["explore"] if explore is None else explore,
            "star_emojis": s["star_emojis"]
            if star_emojis is None
            else star_emojis,
            "display_emoji": s["display_emoji"]
            if display_emoji is None
            else display_emoji,
            "regex": s["regex"] if regex is None else regex,
            "exclude_regex": s["exclude_regex"]
            if exclude_regex is None
            else exclude_regex,
            "ping": s["ping"] if ping is None else ping,
            "color": s["color"] if color is None else color,
        }

        if settings["required"] <= settings["required_remove"]:
            raise discord.InvalidArgument(
                "requiredStars cannot be less than or equal to "
                "requiredRemove"
            )
        if settings["required"] < 1:
            raise discord.InvalidArgument(
                "requiredStars cannot be less than 1"
            )
        if settings["required"] > 500:
            raise discord.InvalidArgument(
                "requiredStars cannot be greater than 500"
            )
        if settings["required_remove"] < -1:
            raise discord.InvalidArgument(
                "requiredRemove cannot be less than -1"
            )
        if settings["required_remove"] > 495:
            raise discord.InvalidArgument(
                "requiredRemove cannot be greater tahn 495"
            )

        await self.bot.db.execute(
            """UPDATE starboards
            SET required = $1,
            required_remove = $2,
            autoreact = $3,
            self_star = $4,
            allow_bots = $5,
            allow_nsfw = $6,
            link_deletes = $7,
            link_edits = $8,
            images_only = $9,
            remove_reactions = $10,
            no_xp = $11,
            explore = $12,
            star_emojis = $13,
            display_emoji = $14,
            regex = $15,
            exclude_regex = $16,
            color = $17,
            ping = $18
            WHERE id = $19""",
            settings["required"],
            settings["required_remove"],
            settings["autoreact"],
            settings["self_star"],
            settings["allow_bots"],
            settings["allow_nsfw"],
            settings["link_deletes"],
            settings["link_edits"],
            settings["images_only"],
            settings["remove_reactions"],
            settings["no_xp"],
            settings["explore"],
            settings["star_emojis"],
            settings["display_emoji"],
            settings["regex"],
            settings["exclude_regex"],
            settings["color"],
            settings["ping"],
            starboard_id,
        )

    async def add_star_emoji(self, starboard_id: int, emoji: str) -> None:
        if type(emoji) is not str:
            raise ValueError("Expected a str for emoji")

        starboard = await self.get(starboard_id)
        if emoji in starboard["star_emojis"]:
            raise errors.AlreadyExists(
                f"{emoji} is already a starEmoji on " f"{starboard['id']}"
            )

        await self.edit(
            starboard_id, star_emojis=starboard["star_emojis"] + [emoji]
        )

    async def remove_star_emoji(self, starboard_id: int, emoji: str) -> None:
        if type(emoji) is not str:
            raise ValueError("Expected a str for emoji")

        starboard = await self.get(starboard_id)
        if emoji not in starboard["star_emojis"]:
            raise errors.DoesNotExist(
                f"{emoji} is already a starEmoji on " f"{starboard['id']}"
            )

        new_emojis = starboard["star_emojis"]
        new_emojis.remove(emoji)

        await self.edit(starboard_id, star_emojis=new_emojis)
