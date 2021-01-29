from discord.ext import commands

from app.classes.bot import Bot
from app import cooldowns
from . import leveling_funcs


class LevelingEvents(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.cooldown = cooldowns.FlexibleCooldownMapping()

    @commands.Cog.listener()
    async def on_star_update(
        self, giver_id: int, receiver_id: int, guild_id: int, points: int
    ) -> None:
        if giver_id == receiver_id:
            return

        # TODO(Circuit): Make this take the rate/per of a guild
        bucket = self.cooldown.get_bucket((giver_id, receiver_id), 3, 60)
        retry_after = bucket.update_rate_limit()
        if retry_after:
            return

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

        leveled_up = None

        async with self.bot.db.pool.acquire() as con:
            await con.execute(
                """UPDATE members
                SET xp = xp + $1,
                stars_received = stars_received + $1
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
            # TODO: Send to guild level up channel
            pass


def setup(bot: Bot) -> None:
    bot.add_cog(LevelingEvents(bot))
