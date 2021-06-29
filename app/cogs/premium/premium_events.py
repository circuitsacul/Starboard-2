from datetime import datetime
from typing import TYPE_CHECKING, List

import discord
from discord.ext import tasks

import config
from app import commands, errors, utils
from app.i18n import t_

from .premium_funcs import redeem_credits

if TYPE_CHECKING:
    from app.classes.bot import Bot


class PremiumEvents(commands.Cog):
    def __init__(self, bot: "Bot"):
        self.bot = bot
        if 0 in self.bot.shard_ids:
            self.check_expired_premium.start()

    @tasks.loop(hours=1)
    async def check_expired_premium(self):
        await self.bot.wait_until_ready()
        now = datetime.utcnow()
        expired_guilds = await self.bot.db.fetch(
            """SELECT * FROM guilds
            WHERE premium_end < $1""",
            now,
        )
        for sql_guild in expired_guilds:
            autoredeemers = await self.bot.db.autoredeem.find_valid(
                int(sql_guild["id"])
            )
            obj = self.bot.get_guild(int(sql_guild["id"]))
            autoredeemed = False
            if obj is not None:
                for ar in autoredeemers:
                    user = await self.bot.cache.fetch_user(int(ar["user_id"]))
                    if not user:
                        continue
                    try:
                        await redeem_credits(
                            self.bot.db,
                            int(sql_guild["id"]),
                            int(ar["user_id"]),
                            1,
                        )
                    except errors.NotEnoughCredits:
                        pass
                    else:
                        await utils.try_send(
                            user,
                            t_(
                                "You have AutoRedeem enabled in {0}, and that "
                                "server ran out of premium, so 3 credits were "
                                "taken from your acccount. You can disable "
                                "AutoRedeem for this server by running "
                                "`sb!autoredeem disable {1}`."
                            ).format(obj.name, obj.id),
                        )
                        autoredeemed = True
                        break
            if autoredeemed:
                continue

            await self.bot.db.execute(
                """UPDATE guilds
                SET premium_end = null
                WHERE id = $1""",
                sql_guild["id"],
            )
            if obj is not None:
                self.bot.dispatch(
                    "guild_log",
                    t_("Premium has expired for this server."),
                    "info",
                    obj,
                )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.guild.id == config.ROLE_SERVER:
            self.bot.dispatch("update_prem_roles", member.id)

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
        if not sql_user:
            return

        donor = (
            sql_user["last_patreon_total"] + sql_user["donation_total"]
        ) != 0
        patron = sql_user["patron_status"] == "yes"

        to_give: List[int] = []
        to_remove: List[int] = []
        if donor:
            to_give += config.DONATE_ROLES
        else:
            to_remove += config.DONATE_ROLES
        if patron:
            to_give += config.PATRON_ROLES
        else:
            to_remove += config.PATRON_ROLES

        to_give_obj: List[discord.Role] = []
        to_remove_obj: List[discord.Role] = []
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
