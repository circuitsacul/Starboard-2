from typing import Optional

import asyncpg
import discord

from app import errors
from app.i18n import t_


class ASChannels:
    def __init__(self, db) -> None:
        self.db = db

    async def get(self, aschannel_id: int) -> Optional[dict]:
        return await self.db.fetchrow(
            """SELECT * FROM aschannels
            WHERE id=$1""",
            aschannel_id,
        )

    async def get_many(self, guild_id: int) -> list[dict]:
        return await self.db.fetch(
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

        is_starboard = await self.db.starboards.get(channel_id) is not None
        if is_starboard:
            raise errors.AlreadyExists(
                t_("That channel is already a starboard!")
            )

        await self.db.guilds.create(guild_id)
        try:
            await self.db.execute(
                """INSERT INTO aschannels (id, guild_id)
                VALUES ($1, $2)""",
                channel_id,
                guild_id,
            )
        except asyncpg.exceptions.UniqueViolationError:
            return True
        return False

    async def delete(self, aschannel_id: int) -> None:
        await self.db.execute(
            """DELETE FROM aschannels
            WHERE id=$1""",
            aschannel_id,
        )

    async def edit(
        self,
        aschannel_id: int,
        emojis: list[str] = None,
        min_chars: int = None,
        require_image: bool = None,
        regex: str = None,
        exclude_regex: str = None,
        delete_invalid: str = None,
    ) -> None:
        asc = await self.get(aschannel_id)
        if not asc:
            raise errors.DoesNotExist(
                t_("No AutoStarChannel found with id {0}.").format(
                    aschannel_id
                )
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
            raise discord.InvalidArgument(
                t_("minChars cannot be less than 0.")
            )
        if settings["min_chars"] > 2000:
            raise discord.InvalidArgument(
                t_("minChars cannot be grater than 2,000.")
            )

        await self.db.execute(
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
        if not aschannel:
            raise errors.NotInDatabase(
                f"Could not find aschannel {aschannel_id}."
            )
        if emoji in aschannel["emojis"]:
            raise errors.AlreadyExists(
                t_("{0} is already an emoji on {1}.").format(
                    emoji, aschannel_id
                )
            )
        new_emojis: list = aschannel["emojis"]
        new_emojis.append(emoji)
        await self.edit(aschannel_id, emojis=new_emojis)

    async def remove_asemojis(self, aschannel_id: int, emoji: str) -> None:
        aschannel = await self.get(aschannel_id)
        if not aschannel:
            raise errors.NotInDatabase(
                f"Could not find aschannel {aschannel_id}."
            )
        if emoji not in aschannel["emojis"]:
            raise errors.DoesNotExist(
                t_("{0} is not an emoji on {1}.").format(emoji, aschannel_id)
            )
        new_emojis: list = aschannel["emojis"]
        new_emojis.remove(emoji)
        await self.edit(aschannel_id, emojis=new_emojis)
