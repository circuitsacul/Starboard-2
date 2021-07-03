from typing import Dict, List, Optional, Tuple

import discord

from app.classes.bot import Bot
from app.cogs.cache.cache import cached


def pretty_permrole_string(
    role: Dict[str, bool], guild: discord.Guild
) -> Tuple[str, str]:
    obj = guild.get_role(role["role_id"])
    role_name = obj.name if obj else f"Delete Role {role['role_id']}"
    role_name = "{0}. {1}".format(role["index"], role_name)

    result = pretty_perm_string(role)

    return role_name, result


def pretty_perm_string(perms: Dict[str, bool]):
    def setting(name: str) -> str:
        mapping = {
            None: "<:slash:860514365497016331>",
            True: "✅",
            False: "❌",
        }
        return mapping[perms[name]]

    result = (
        f"allowCommands: {setting('allow_commands')}\n"
        f"onStarboard: {setting('on_starboard')}\n"
        f"giveStars: {setting('give_stars')}\n"
        f"gainXp: {setting('gain_xp')}\n"
        f"posRoles: {setting('pos_roles')}\n"
        f"xpRoles: {setting('xp_roles')}\n"
    )
    return result


@cached(
    "filter_permissions",
    30,
    cache_args=[1, 2, 3, 4],
)
async def get_perms(
    bot: Bot,
    roles: List[int],
    guild_id: int,
    channel_id: Optional[int],
    starboard_id: Optional[int],
) -> Dict[str, bool]:
    groups = await bot.db.fetch(
        """SELECT * FROM permgroups
        WHERE guild_id=$1
        AND (
            channels='{}'
            OR $2::numeric IS NULL
            OR $2::numeric=any(channels)
        )
        AND (
            starboards='{}'
            OR $3::numeric IS NULL
            OR $3::numeric=any(starboards)
        )
        """,
        guild_id,
        channel_id,
        starboard_id,
    )

    permroles = []
    for g in groups:
        permroles += await bot.db.fetch(
            """SELECT * FROM permroles
            WHERE permgroup_id=$1
            AND role_id=any($2::numeric[])""",
            g["id"],
            roles,
        )

    perms = {
        "allow_commands": True,
        "on_starboard": True,
        "give_stars": True,
        "gain_xp": True,
        "pos_roles": True,
        "xp_roles": True,
    }
    for pr in permroles:
        for key in perms.keys():
            if pr[key] is None:
                continue
            perms[key] = pr[key]

    return perms
