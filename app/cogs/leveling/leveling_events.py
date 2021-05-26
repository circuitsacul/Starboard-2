from typing import Optional

from app import commands, cooldowns
from app.classes.bot import Bot
from app.cogs.permroles import pr_functions

from . import leveling_funcs


class LevelingEvents(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.cooldown = cooldowns.FlexibleCooldownMapping()

    @commands.Cog.listener()
    async def on_star_update(
        self,
        giver_id: int,
        receiver_id: int,
        guild_id: int,
        channel_id: int,
        points: int,
    ) -> None:
        if giver_id == receiver_id and False:  # TODO revert "and False"
            return

        # I need to check two things:
        # 1. That the star giver has permission to star messages
        # 2. That the star receiver has the gainXP permission.
        # Steps:
        # 1. We first calculate all valid starEmojis, ignoring any starboards
        #    where the giver cannot give stars.
        # 2. If the emoji that was given is in still valid, then
        #    check if the receiver can receive XP *based on the channel*,
        #    not starboard.

        guild = self.bot.get_guild(guild_id)
        _result = await self.bot.cache.get_members(
            [int(giver_id), int(receiver_id)], guild
        )
        if giver_id not in _result:
            return
        if receiver_id not in _result:
            return
        receiver = _result[receiver_id]

        receiver_perms = await pr_functions.get_perms(
            self.bot,
            [r.id for r in receiver.roles],
            guild_id,
            channel_id,
            None,
        )
        if not receiver_perms["gain_xp"]:
            gain_xp = False
        else:
            gain_xp = True

        await self.bot.db.members.create(giver_id, guild_id)
        sql_giver = await self.bot.db.members.get(giver_id, guild_id)
        await self.bot.db.members.create(receiver_id, guild_id)

        await self.bot.db.execute(
            """UPDATE members SET stars_given = stars_given + $1
            WHERE user_id=$2 AND guild_id=$3""",
            points,
            sql_giver["user_id"],
            sql_giver["guild_id"],
        )

        await self.bot.db.execute(
            """UPDATE members
            SET stars_received = stars_received + $1
            WHERE user_id=$2 AND guild_id=$3""",
            points,
            receiver_id,
            guild_id,
        )

        if not gain_xp:
            return

        leveled_up: Optional[int] = None

        sql_guild = await self.bot.db.guilds.get(guild_id)
        cooldown, per = sql_guild["xp_cooldown"], sql_guild["xp_cooldown_per"]

        if per != 0 and sql_guild["xp_cooldown_on"]:
            bucket = self.cooldown.get_bucket(
                (giver_id, receiver_id), cooldown, per
            )
            retry_after = bucket.update_rate_limit()
            if retry_after:
                return

        async with self.bot.db.pool.acquire() as con:
            await con.execute(
                """UPDATE members
                SET xp = xp + $1
                WHERE user_id=$2 AND guild_id=$3""",
                points,
                receiver_id,
                guild_id,
            )
            sql_receiver = await con.fetchrow(
                """SELECT * FROM members WHERE user_id=$1
                AND guild_id=$2 FOR UPDATE""",
                receiver_id,
                guild_id,
            )
            new_level = leveling_funcs.current_level(sql_receiver["xp"])
            if new_level > sql_receiver["level"]:
                leveled_up = new_level
                await con.execute(
                    """UPDATE members SET level=$1
                    WHERE user_id=$2 AND guild_id=$3""",
                    new_level,
                    receiver_id,
                    guild_id,
                )

        if leveled_up:
            guild = self.bot.get_guild(guild_id)
            await self.bot.set_locale(guild)
            if not receiver.bot:
                self.bot.dispatch("level_up", guild, receiver, leveled_up)

        self.bot.dispatch("update_xpr", guild.id, receiver.id)
        self.bot.dispatch("update_pr", guild.id, receiver.id)


def setup(bot: Bot) -> None:
    bot.add_cog(LevelingEvents(bot))
