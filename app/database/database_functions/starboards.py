from typing import Optional

import asyncpg
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

    async def star_emojis(self, guild_id: int) -> list[str]:
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

    async def get_many(self, guild_id: int) -> list[dict]:
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
        await self.db.execute(
            """UPDATE starboards
            SET webhook_url=$1
            WHERE id=$2""",
            url,
            starboard_id,
        )
        await self._starboard_edited(starboard_id)

    async def set_webhook_name(self, starboard_id: int, name: str):
        await self.db.execute(
            """UPDATE starboards
            SET webhook_name=$1
            WHERE id=$2""",
            name,
            starboard_id,
        )
        await self._starboard_edited(starboard_id)

    async def set_webhook_avatar(self, starboard_id: int, url: str):
        await self.db.execute(
            """UPDATE starboards
            SET webhook_avatar=$1
            WHERE id=$2""",
            url,
            starboard_id,
        )
        await self._starboard_edited(starboard_id)

    async def edit(
        self,
        starboard_id: int,
        required: int = None,
        required_remove: int = None,
        autoreact: bool = None,
        self_star: bool = None,
        allow_bots: bool = None,
        link_deletes: bool = None,
        link_edits: bool = None,
        images_only: bool = None,
        no_xp: bool = None,
        explore: bool = None,
        star_emojis: list[str] = None,
        display_emoji: str = None,
        ping: bool = None,
        regex: str = None,
        exclude_regex: str = None,
        color: int = None,
        channel_bl: list[int] = None,
        channel_wl: list[int] = None,
        use_webhook: bool = None,
    ) -> None:
        s = await self.get(starboard_id)
        if not s:
            raise errors.NotStarboard(starboard_id)

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
            "link_deletes": s["link_deletes"]
            if link_deletes is None
            else link_deletes,
            "link_edits": s["link_edits"]
            if link_edits is None
            else link_edits,
            "images_only": s["images_only"]
            if images_only is None
            else images_only,
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
            "channel_bl": s["channel_bl"]
            if channel_bl is None
            else channel_bl,
            "channel_wl": s["channel_wl"]
            if channel_wl is None
            else channel_wl,
            "use_webhook": s["use_webhook"]
            if use_webhook is None
            else use_webhook,
        }

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

        await self.db.execute(
            """UPDATE starboards
            SET required = $1,
            required_remove = $2,
            autoreact = $3,
            self_star = $4,
            allow_bots = $5,
            link_deletes = $6,
            link_edits = $7,
            images_only = $8,
            no_xp = $9,
            explore = $10,
            star_emojis = $11,
            display_emoji = $12,
            regex = $13,
            exclude_regex = $14,
            color = $15,
            ping = $16,
            channel_bl = $17,
            channel_wl = $18,
            use_webhook = $19
            WHERE id = $20""",
            settings["required"],
            settings["required_remove"],
            settings["autoreact"],
            settings["self_star"],
            settings["allow_bots"],
            settings["link_deletes"],
            settings["link_edits"],
            settings["images_only"],
            settings["no_xp"],
            settings["explore"],
            settings["star_emojis"],
            settings["display_emoji"],
            settings["regex"],
            settings["exclude_regex"],
            settings["color"],
            settings["ping"],
            settings["channel_bl"],
            settings["channel_wl"],
            settings["use_webhook"],
            starboard_id,
        )

        await self._starboard_edited(starboard_id, int(s["guild_id"]))

    async def add_star_emoji(self, starboard_id: int, emoji: str) -> None:
        if type(emoji) is not str:
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
        if type(emoji) is not str:
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
