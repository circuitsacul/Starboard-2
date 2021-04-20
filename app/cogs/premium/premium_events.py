import typing

import discord
from discord.ext import commands

import config

if typing.TYPE_CHECKING:
    from app.classes.bot import Bot


class PremiumEvents(commands.Cog):
    def __init__(self, bot: "Bot"):
        self.bot = bot

    @commands.Cog.listener()
    async def on_update_prem_roles(self, user_id: int):
        prem_role_server_id = config.ROLE_SERVER
        if not prem_role_server_id:
            return

        guild = self.bot.get_guild(prem_role_server_id)
        if not guild:
            return

        _result = await self.bot.cache.get_members([user_id], guild)
        if user_id not in _result:
            return
        member: discord.Member = _result[user_id]
        curr_roles = [r.id for r in member.roles]

        sql_user = await self.bot.db.users.get(user_id)

        donor = (
            sql_user["last_patreon_total"] + sql_user["donation_total"]
        ) != 0
        patron = sql_user["patron_status"] == "yes"

        to_give: list[int] = []
        to_remove: list[int] = []
        if donor:
            to_give += config.DONATE_ROLES
        else:
            to_remove += config.DONATE_ROLES
        if patron:
            to_give += config.PATRON_ROLES
        else:
            to_remove += config.PATRON_ROLES

        to_give_obj: list[discord.Role] = []
        to_remove_obj: list[discord.Role] = []
        for rid in to_give:
            if rid in curr_roles:
                continue
            obj = guild.get_role(rid)
            if not obj:
                continue
            to_give_obj.append(obj)
        for rid in to_remove:
            if rid not in curr_roles:
                continue
            obj = guild.get_role(rid)
            if not obj:
                continue
            to_remove_obj.append(obj)

        if to_give_obj != []:
            await member.add_roles(*to_give_obj)
        if to_remove_obj != []:
            await member.remove_roles(*to_remove_obj)


def setup(bot: "Bot"):
    bot.add_cog(PremiumEvents(bot))
