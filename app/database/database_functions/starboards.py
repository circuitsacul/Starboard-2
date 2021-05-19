from typing import Any, Dict, List, Optional, Union

import asyncpg
import buildpg
from aiocache import Cache, SimpleMemoryCache
from discord.ext import commands

from app import errors
from app.i18n import t_


class Starboards:
    def __init__(self, db) -> None:
        self.db = db
        self.cache: SimpleMemoryCache = Cache(namespace="starboards", ttl=10)
        self.many_cache: SimpleMemoryCache = Cache(namespace="many_sb", ttl=10)
        self.emoji_cache: SimpleMemoryCache = Cache(
            namespace="sb_emojis", ttl=10
        )

    async def _starboard_edited(
        self, starboard_id: int, guild_id: Optional[int] = None
    ):
        await self.cache.delete(starboard_id)
        if guild_id:
            await self.emoji_cache.delete(guild_id)
            await self.many_cache.delete(guild_id)

    async def star_emojis(self, guild_id: int) -> List[str]:
        r = await self.emoji_cache.get(guild_id)
        if r:
            return r

        _emojis = await self.db.execute(
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

        await self.emoji_cache.set(guild_id, emojis)
        return emojis

    async def get(self, starboard_id: int) -> Optional[dict]:
        r = await self.cache.get(starboard_id)
        if r:
            return r
        sql_starboard = await self.db.fetchrow(
            """SELECT * FROM starboards
            WHERE id=$1""",
            starboard_id,
        )
        await self.cache.set(starboard_id, sql_starboard)
        return sql_starboard

    async def get_many(self, guild_id: int) -> List[Dict[Any, Any]]:
        r = await self.many_cache.get(guild_id)
        if r:
            return r
        sql_starboards = await self.db.fetch(
            """SELECT * FROM starboards
            WHERE guild_id=$1""",
            guild_id,
        )
        await self.many_cache.set(guild_id, sql_starboards)
        return sql_starboards

    async def create(
        self, channel_id: int, guild_id: int, check_first: bool = True
    ) -> bool:
        if check_first:
            exists = await self.get(channel_id) is not None
            if exists:
                return True

        is_asc = await self.db.aschannels.get(channel_id) is not None
        if is_asc:
            raise errors.CannotBeStarboardAndAutostar()

        await self.db.guilds.create(guild_id)
        try:
            await self.db.execute(
                """INSERT INTO starboards (id, guild_id)
                VALUES ($1, $2)""",
                channel_id,
                guild_id,
            )
        except asyncpg.exceptions.UniqueViolationError:
            return True

        await self._starboard_edited(channel_id, guild_id)

        return False

    async def delete(self, starboard_id: int) -> None:
        s = await self.get(starboard_id)
        if not s:
            return

        await self.db.execute(
            """DELETE FROM starboards WHERE id=$1""", starboard_id
        )

        await self._starboard_edited(starboard_id, int(s["guild_id"]))

    async def set_webhook(self, starboard_id: int, url: Optional[str]):
        """This is not a user customizable setting.

        It does not belong under edit."""
        await self.db.execute(
            """UPDATE starboards
            SET webhook_url=$1
            WHERE id=$2""",
            url,
            starboard_id,
        )
        await self._starboard_edited(starboard_id)

    async def edit(
        self, starboard_id: int, **attrs: Union[int, bool, str, None]
    ) -> None:
        s = await self.get(starboard_id)
        if not s:
            raise errors.NotStarboard(starboard_id)

        valid_settings = [
            "required",
            "required_remove",
            "autoreact",
            "self_star",
            "allow_bots",
            "link_deletes",
            "link_edits",
            "images_only",
            "no_xp",
            "explore",
            "star_emojis",
            "display_emoji",
            "regex",
            "exclude_regex",
            "color",
            "ping",
            "channel_bl",
            "channel_wl",
            "use_webhook",
            "remove_invalid",
            "webhook_avatar",
            "webhook_name",
        ]

        settings = {}
        for key in valid_settings:
            settings[key] = attrs.get(key, s[key])

        if settings["required"] <= settings["required_remove"]:
            raise commands.BadArgument(
                t_(
                    "requiredStars cannot be less than or equal to "
                    "requiredRemove."
                )
            )
        if settings["required"] < 1:
            raise commands.BadArgument(
                t_("requiredStars cannot be less than 1.")
            )
        if settings["required"] > 500:
            raise commands.BadArgument(
                t_("requiredStars cannot be greater than 500.")
            )
        if settings["required_remove"] < -1:
            raise commands.BadArgument(
                t_("requiredRemove cannot be less than -1.")
            )
        if settings["required_remove"] > 495:
            raise commands.BadArgument(
                t_("requiredRemove cannot be greater than 495.")
            )

        query, args = buildpg.render(
            """UPDATE starboards
            SET required = :required,
            required_remove = :required_remove,
            autoreact = :autoreact,
            self_star = :self_star,
            allow_bots = :allow_bots,
            link_deletes = :link_deletes,
            link_edits = :link_edits,
            images_only = :images_only,
            no_xp = :no_xp,
            explore = :explore,
            star_emojis = :star_emojis,
            display_emoji = :display_emoji,
            regex = :regex,
            exclude_regex = :exclude_regex,
            color = :color,
            ping = :ping,
            channel_bl = :channel_bl,
            channel_wl = :channel_wl,
            use_webhook = :use_webhook,
            remove_invalid = :remove_invalid,
            webhook_avatar = :webhook_avatar,
            webhook_name = :webhook_name
            WHERE id = :starboard_id""",
            **settings,
            starboard_id=starboard_id,
        )
        await self.db.execute(query, *args)
        await self._starboard_edited(starboard_id, int(s["guild_id"]))

    async def add_star_emoji(self, starboard_id: int, emoji: str) -> None:
        if not isinstance(emoji, str):
            raise ValueError("Expected a str for emoji.")

        starboard = await self.get(starboard_id)
        if not starboard:
            raise errors.NotInDatabase(
                f"Could not find starboard {starboard_id}."
            )
        if emoji in starboard["star_emojis"]:
            raise errors.AlreadySBEmoji(emoji, starboard["id"])

        await self.edit(
            starboard_id, star_emojis=starboard["star_emojis"] + [emoji]
        )

    async def remove_star_emoji(self, starboard_id: int, emoji: str) -> None:
        if not isinstance(emoji, str):
            raise ValueError("Expected a str for emoji.")

        starboard = await self.get(starboard_id)
        if not starboard:
            raise errors.NotInDatabase(
                f"Could not find starboard {starboard_id}."
            )
        if emoji not in starboard["star_emojis"]:
            raise errors.AlreadySBEmoji(emoji, starboard["id"])

        new_emojis = starboard["star_emojis"]
        new_emojis.remove(emoji)

        await self.edit(starboard_id, star_emojis=new_emojis)
