from typing import List, Optional

import asyncpg
import discord

from app import errors


class ASChannels:
    def __init__(self, bot) -> None:
        self.bot = bot

    async def get(self, aschannel_id: int) -> Optional[dict]:
        return await self.bot.db.fetchrow(
            """SELECT * FROM aschannels
            WHERE id=$1""",
            aschannel_id,
        )

    async def get_many(self, guild_id: int) -> List[dict]:
        return await self.bot.db.fetch(
            """SELECT * FROM aschannels
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

        is_starboard = await self.bot.db.starboards.get(channel_id) is not None
        if is_starboard:
            raise errors.AlreadyExists("That channel is already a starboard!")

        await self.bot.db.guilds.create(guild_id)
        try:
            await self.bot.db.execute(
                """INSERT INTO aschannels (id, guild_id)
                VALUES ($1, $2)""",
                channel_id,
                guild_id,
            )
        except asyncpg.exceptions.UniqueViolationError:
            return True
        return False

    async def delete(self, aschannel_id: int) -> None:
        await self.bot.db.execute(
            """DELETE FROM aschannels
            WHERE id=$1""",
            aschannel_id,
        )

    async def edit(
        self,
        aschannel_id: int,
        emojis: List[str] = None,
        min_chars: int = None,
        require_image: bool = None,
        regex: str = None,
        exclude_regex: str = None,
        delete_invalid: str = None,
    ) -> None:
        asc = await self.get(aschannel_id)
        if not asc:
            raise errors.DoesNotExist(
                f"No AutoStarChannel found with id {aschannel_id}"
            )

        settings = {
            "emojis": asc["emojis"] if emojis is None else emojis,
            "min_chars": asc["min_chars"] if min_chars is None else min_chars,
            "require_image": asc["require_image"]
            if require_image is None
            else require_image,
            "delete_invalid": asc["delete_invalid"]
            if delete_invalid is None
            else delete_invalid,
            "regex": asc["regex"] if regex is None else regex,
            "exclude_regex": asc["exclude_regex"]
            if exclude_regex is None
            else exclude_regex,
        }

        if settings["min_chars"] < 0:
            raise discord.InvalidArgument("minChars cannot be less than 0")
        if settings["min_chars"] > 2000:
            raise discord.InvalidArgument(
                "minChars cannot be grater than 2,000"
            )

        await self.bot.db.execute(
            """UPDATE aschannels
            SET emojis=$2::text[],
            min_chars=$3,
            require_image=$4,
            delete_invalid=$5,
            regex=$6,
            exclude_regex=$7
            WHERE id=$1""",
            aschannel_id,
            settings["emojis"],
            settings["min_chars"],
            settings["require_image"],
            settings["delete_invalid"],
            settings["regex"],
            settings["exclude_regex"],
        )

    async def add_asemoji(self, aschannel_id: int, emoji: str) -> None:
        aschannel = await self.get(aschannel_id)
        if emoji in aschannel["emojis"]:
            raise errors.AlreadyExists(
                f"{emoji} is already an emoji on {aschannel_id}"
            )
        new_emojis: List = aschannel["emojis"]
        new_emojis.append(emoji)
        await self.edit(aschannel_id, emojis=new_emojis)

    async def remove_asemojis(self, aschannel_id: int, emoji: str) -> None:
        aschannel = await self.get(aschannel_id)
        if emoji not in aschannel["emojis"]:
            raise errors.DoesNotExist(
                f"{emoji} is not an emoji on {aschannel_id}"
            )
        new_emojis: List = aschannel["emojis"]
        new_emojis.remove(emoji)
        await self.edit(aschannel_id, emojis=new_emojis)
