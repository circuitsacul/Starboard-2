from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

import discord
from discord.ext import tasks

from app import commands
from app.cogs.permroles import pr_functions
from app.i18n import t_

if TYPE_CHECKING:
    from app.classes.bot import Bot


async def remove_pr(member: discord.Member, bot: "Bot", *roles: discord.Role):
    try:
        await member.remove_roles(*roles)
    except discord.Forbidden:
        pass
    for r in roles:
        await bot.db.posroles.remove_posrole(member.id, r.id)


async def add_pr(member: discord.Member, bot: "Bot", *roles: discord.Role):
    try:
        await member.add_roles(*roles)
    except discord.Forbidden:
        pass
    for r in roles:
        await bot.db.posroles.give_posrole(member.id, r.id, member.guild.id)


async def get_proper_posrole(
    bot: "Bot",
    guild: discord.Guild,
    member_id: int,
    xp: int,
) -> Tuple[Optional[int], Optional[int]]:
    """Gets the PositionRole a member should belong to.

    :param bot: The bot instance.
    :type bot: Bot
    :param guild: The guild in which to check posroles.
    :type guild: discord.Guild
    :param member_id: The id of the member to check.
    :type member_id: int
    :param xp: The ammount of xp this member has.
    :type xp: int
    :return: 1) The id of the role they should have, 2)
        Optionally the member who was replaced.
    :rtype: Tuple[Optional[int], Optional[int]]
    """

    _all_posroles = await bot.db.posroles.get_many(guild.id)
    all_posroles: List[Tuple[discord.Role, Dict[str, Any]]] = [
        (
            guild.get_role(r["role_id"]),
            r,
        )
        for r in _all_posroles
    ]
    all_posroles.sort(
        key=lambda r: r[0].position,
        reverse=True,
    )

    for obj, pr in all_posroles:
        is_current = False

        _current_pr_members = await bot.db.posroles.get_posrole_members(obj.id)
        if member_id in _current_pr_members:
            is_current = True

        current_pr_members = [
            await bot.db.members.get(mid, guild.id)
            for mid in _current_pr_members
        ]

        if len(current_pr_members) < pr["max_users"] + (
            1 if is_current else 0
        ):
            return obj.id, None

        least_xp = list(sorted(current_pr_members, key=lambda m: m["xp"]))[0]
        if xp > least_xp["xp"]:
            return obj.id, least_xp["user_id"]
    return None, None


class PREvents(commands.Cog):
    def __init__(self, bot: "Bot"):
        self.bot = bot
        self.queue: Dict[int, List[int]] = {}
        self.update_pos_roles.start()

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        posrole = await self.bot.db.posroles.get(role.id)

        if not posrole:
            return

        await self.bot.db.posroles.delete(role.id)
        self.bot.dispatch(
            "guild_log",
            "info",
            t_(
                f"The role **{role.name}** was deleted, so I "
                "removed that PosRole."
            ),
        )

    @commands.Cog.listener()
    async def on_update_pr(self, guild_id: int, user_id: int):
        self.queue.setdefault(guild_id, [])
        self.queue[guild_id].append(user_id)

    @tasks.loop(seconds=5)
    async def update_pos_roles(self):
        for gid in list(self.queue.keys()):
            to_update = self.queue[gid]
            if len(to_update) == 0:
                del self.queue[gid]
                continue

            n = to_update.pop()
            guild: discord.Guild = self.bot.get_guild(gid)
            _member = await self.bot.cache.get_members([n], guild)
            if n not in _member:
                continue
            member = _member[n]

            perms = await pr_functions.get_perms(
                self.bot,
                [r.id for r in member.roles],
                member.guild.id,
                None,
                None,
            )
            if perms["pos_roles"]:
                role, replaced = await get_proper_posrole(
                    self.bot,
                    guild,
                    member.id,
                    (await self.bot.db.members.get(member.id, guild.id))["xp"],
                )
            else:
                role = replaced = None

            _all_posroles = await self.bot.db.posroles.get_many(guild.id)
            to_remove = [guild.get_role(r["role_id"]) for r in _all_posroles]
            if role:
                role = guild.get_role(role)
                to_remove.remove(role)
                to_add = [role]
            else:
                to_add = []

            await add_pr(member, self.bot, *to_add)
            await remove_pr(member, self.bot, *to_remove)

            if replaced:
                self.bot.dispatch("update_pr", guild.id, replaced)


def setup(bot: "Bot"):
    bot.add_cog(PREvents(bot))
