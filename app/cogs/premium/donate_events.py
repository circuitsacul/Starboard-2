import os
import typing

import discord
from discord.ext import commands

import config
from app.i18n import t_

if typing.TYPE_CHECKING:
    from app.classes.bot import Bot


async def alert_donator(bot: "Bot", user_id: int, message: str):
    user = await bot.cache.fetch_user(user_id)
    if not user:
        return
    try:
        await user.send(message)
    except discord.Forbidden:
        pass


class DonateEvents(commands.Cog):
    def __init__(self, bot: "Bot"):
        self.bot = bot
        self.donatebot_token = os.getenv("DONATEBOT_TOKEN")

    @commands.Cog.listener()
    async def on_donatebot_event(self, data: dict, auth: str):
        if auth != self.donatebot_token:
            return
        pid = data.get("product_id")
        if pid not in config.DONATEBOT_PRODUCT_IDS:
            return

        discord_id = int(data["raw_buyer_id"])
        await self.bot.db.users.create(discord_id, False)

        await self.bot.db.execute(
            """UPDATE users
            SET credits = credits + $1
            WHERE id = $2""",
            round(float(data["price"])),
            discord_id,
        )

        await alert_donator(
            self.bot,
            discord_id,
            t_(
                "We received your donation of ${0} through donatebot, "
                "and you have gained {1} credit(s). If you have any "
                "questions feel free to dm Circuit#5585. Thanks for "
                "your donation!"
            ).format(data["price"], round(float(data["price"]))),
        )


def setup(bot: "Bot"):
    if 0 in bot.shard_ids:
        bot.add_cog(DonateEvents(bot))
