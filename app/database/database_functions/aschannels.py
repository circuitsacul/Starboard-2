from typing import TYPE_CHECKING, Dict, List, Optional

import asyncpg
import buildpg
import cachetools

from app import commands, errors
from app.cogs.premium.premium_funcs import can_increase, limit_for
from app.constants import MISSING
from app.i18n import t_

if TYPE_CHECKING:
    from app.database.database import Database


class ASChannels:
    def __init__(self, db: "Database") -> None:
        self.db = db
        self.id_cache = cachetools.TTLCache(5_000, 30)

    def edited(self, aschannel_id: int):
        if aschannel_id in self.id_cache:
            del self.id_cache[aschannel_id]

    async def get(self, aschannel_id: int) -> Optional[dict]:
        r = self.id_cache.get(aschannel_id, default=MISSING)
        if r is not MISSING:
            return r

        r = await self.db.fetchrow(
            """SELECT * FROM aschannels
            WHERE id=$1""",
            aschannel_id,
        )
        self.id_cache[aschannel_id] = r
        return r

    async def get_many(self, guild_id: int) -> List[Dict]:
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
            raise errors.CannotBeStarboardAndAutostar()
        count = await self.db.fetchval(
            """SELECT COUNT(1) FROM aschannels WHERE guild_id=$1""",
            guild_id,
        )
        limit = await limit_for("aschannels", guild_id, self.db)
        if count >= limit:
            raise errors.AutoStarChannelLimitReached(
                await can_increase("aschannels", guild_id, self.db)
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
        self.edited(channel_id)
        return False

    async def delete(self, aschannel_id: int) -> None:
        await self.db.execute(
            """DELETE FROM aschannels
            WHERE id=$1""",
            aschannel_id,
        )
        self.edited(aschannel_id)

    async def edit(
        self,
        aschannel_id: int,
        **attrs,
    ) -> None:
        asc = await self.get(aschannel_id)
        if not asc:
            raise errors.NotAutoStarChannel(str(aschannel_id))

        valid_settings = [
            "emojis",
            "min_chars",
            "max_chars",
            "require_image",
            "regex",
            "exclude_regex",
            "delete_invalid",
        ]

        settings = {}
        for key in valid_settings:
            settings[key] = attrs.get(key, asc[key])

        if settings["min_chars"] < 0:
            raise commands.BadArgument(t_("minChars cannot be less than 0."))
        if settings["min_chars"] > 4_000:
            raise commands.BadArgument(
                t_("minChars cannot be greater than 4,000.")
            )
        if (settings["max_chars"] or 0) < 0:
            raise commands.BadArgument(t_("maxChars cannot be less than 0."))
        if (settings["max_chars"] or 0) > 4_000:
            raise commands.BadArgument(
                t_("maxChars cannot be greater than 4,000.")
            )

        asemojis_limit = await limit_for(
            "asemojis", int(asc["guild_id"]), self.db
        )
        if len(settings["emojis"]) > asemojis_limit and len(
            settings["emojis"]
        ) > len(asc["emojis"]):
            raise errors.AsEmojiLimitReached(
                await can_increase("asemojis", int(asc["guild_id"]), self.db)
            )

        query, args = buildpg.render(
            """UPDATE aschannels
            SET emojis=:emojis,
            min_chars=:min_chars,
            max_chars=:max_chars,
            require_image=:require_image,
            delete_invalid=:delete_invalid,
            regex=:regex,
            exclude_regex=:exclude_regex
            WHERE id=:asc_id""",
            **settings,
            asc_id=aschannel_id,
        )

        await self.db.execute(query, *args)
        self.edited(aschannel_id)

    async def add_asemoji(self, aschannel_id: int, emoji: str) -> None:
        aschannel = await self.get(aschannel_id)
        if not aschannel:
            raise errors.NotInDatabase(
                f"Could not find aschannel {aschannel_id}."
            )
        if emoji in aschannel["emojis"]:
            raise errors.AlreadyASEmoji(emoji, aschannel_id)
        new_emojis: list = aschannel["emojis"] + [emoji]
        await self.edit(aschannel_id, emojis=new_emojis)

    async def remove_asemojis(self, aschannel_id: int, emoji: str) -> None:
        aschannel = await self.get(aschannel_id)
        if not aschannel:
            raise errors.NotInDatabase(
                f"Could not find aschannel {aschannel_id}."
            )
        if emoji not in aschannel["emojis"]:
            raise errors.NotASEmoji(emoji, str(aschannel_id))
        new_emojis: list = aschannel["emojis"].copy()
        new_emojis.remove(emoji)
        await self.edit(aschannel_id, emojis=new_emojis)
