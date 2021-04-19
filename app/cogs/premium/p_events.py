import asyncio
import os
import typing

import discord
from discord.ext import commands, tasks

from app.i18n import t_

from . import patreon

if typing.TYPE_CHECKING:
    from app.classes.bot import Bot


async def alert_patron(bot: "Bot", user_id: int, message: str):
    user = await bot.cache.fetch_user(321733774414970882)
    # FIXME: Make this DM the actual patron
    try:
        await user.send(f"{message} : {user_id}")
    except discord.Forbidden:
        pass


class PremiumEvents(commands.Cog):
    def __init__(self, bot: "Bot"):
        self.bot = bot

        self.access_token = os.getenv("PATREON_TOKEN")
        self.client = patreon.API(self.access_token, bot)

        self.patron_loop.start()

    @tasks.loop(minutes=1)
    async def patron_loop(self):
        await self.bot.wait_until_ready()
        all_patrons = await self.get_all_patrons()
        all_patron_ids = [
            p["discord_id"] for p in all_patrons if p["discord_id"] is not None
        ]

        for patron in all_patrons:
            if patron["discord_id"] is None:
                continue

            await self.bot.db.users.create(int(patron["discord_id"]), False)
            sql_user = await self.bot.db.users.get(int(patron["discord_id"]))

            if patron["total"] > sql_user["last_patreon_total"]:
                to_give = patron["total"] - sql_user["last_patreon_total"]
                await self.bot.db.execute(
                    """UPDATE users
                    SET last_patreon_total=$1,
                    credits = credits + $2
                    WHERE id=$3""",
                    patron["total"],
                    to_give,
                    sql_user["id"],
                )

            text = None
            await self.bot.db.execute(
                """UPDATE users SET last_known_monthly=$1
                WHERE id=$2""",
                patron["payment"],
                sql_user["id"],
            )
            if patron["declined"] and sql_user["patron_status"] != "declined":
                await self.bot.db.users.set_patron_status(
                    int(patron["discord_id"]), "declined"
                )
                text = t_(
                    "Looks like your payment on patreon has been declined. "
                    "Please make sure that you entered your info on patreon "
                    "correctly, and feel free to DM @Circuit#5585 for help."
                )
            elif sql_user["patron_status"] == "no":
                await self.bot.db.users.set_patron_status(
                    int(patron["discord_id"]), "yes"
                )
                text = t_(
                    "Thanks for becoming a patron! Each $ that is sent "
                    "through patreon will be converted to 1 credit. DM "
                    "`@Circuit#5585` if you have any questions.\n\nYour "
                    "support is greatly appreciated."
                )
            elif sql_user["last_known_monthly"] != patron["payment"]:
                text = t_(
                    "Just wanted to alert you that your montly pledge on "
                    "Patreon has changed from ${0} to ${1}. Thanks for "
                    "supporting Starboard!"
                ).format(sql_user["last_known_monthly"], patron["payment"])

            if text:
                await alert_patron(self.bot, int(sql_user["id"]), text)

        # Check for removed/cancelled patrons
        cancelled_patrons = await self.bot.db.fetch(
            """SELECT * FROM users WHERE patron_status!='no'
            AND NOT id=any($1)""",
            all_patron_ids,
        )
        for p in cancelled_patrons:
            await self.bot.db.execute(
                """UPDATE users
                SET last_known_monthly=0,
                patron_status='no'
                WHERE id=$1""",
                p["id"],
            )
            await alert_patron(
                self.bot,
                int(p["id"]),
                t_(
                    "It looks like you removed your pledge on Patreon. "
                    "We're sorry to see you go, but we are still grateful "
                    "for all of your previous support.\n\nYou won't gain "
                    "any more credits automatically, but you will *not* "
                    "loose any you currently have."
                ),
            )

    async def get_all_patrons(self) -> list[dict]:
        """Get the list of all patrons"""
        # return [{
        #    "name": "Lucas",
        #    "payment": 1,
        #    "declined": True,
        #    "total": 15,
        #    "discord_id": 321733774414970882
        # }]

        patrons = []

        # Get the campaign id
        campaign_resource = await self.client.fetch_campaign()
        campaign_id = campaign_resource.data()[0].id()

        # Get all the pledgers
        all_pledgers = []  # Contains the list of all pledgers
        cursor = None  # Allows us to walk through pledge pages
        stop = False

        while not stop:
            # Get the resources of the current pledge page
            # Each page contains 25 pledgers, also
            # fetches the pledge info such as the total
            # $ sent and the date of pledge end
            pledge_resource = await self.client.fetch_page_of_pledges(
                campaign_id,
                25,
                cursor=cursor,
                fields={
                    "pledge": [
                        "total_historical_amount_cents",
                        "declined_since",
                    ]
                },
            )

            # Update cursor
            cursor = await self.client.extract_cursor(pledge_resource)

            # Add data to the list of pledgers
            all_pledgers += pledge_resource.data()

            # If there is no more page, stop the loop
            if not cursor:
                stop = True
                break

        # Get the pledgers info and add the premium status
        for pledger in all_pledgers:
            await asyncio.sleep(0)

            payment = 0
            total_paid = 0
            is_declined = False

            # Get the date of declined pledge
            # False if the pledge has not been declined
            declined_since = pledger.attribute("declined_since")
            total_paid = int(
                pledger.attribute("total_historical_amount_cents") / 100
            )

            # Get the pledger's discord ID
            try:
                discord_id = int(
                    pledger.relationship("patron").attribute(
                        "social_connections"
                    )["discord"]["user_id"]
                )
            except Exception:
                discord_id = None

            # Get the reward tier of the player
            if pledger.relationships()["reward"]["data"]:
                payment = int(
                    pledger.relationship("reward").attribute("amount_cents")
                    / 100
                )

            # Check if the patron has declined his pledge
            if declined_since is not None:
                is_declined = True

            # Add patron data to the patrons list
            patrons.append(
                {
                    "name": pledger.relationship("patron").attribute(
                        "first_name"
                    ),
                    "payment": int(payment),
                    "declined": is_declined,
                    "total": int(total_paid),
                    "discord_id": int(discord_id),
                }
            )

        return patrons


def setup(bot: "Bot"):
    if 0 in bot.shard_ids:
        # Only the first cluster should run this loop
        bot.add_cog(PremiumEvents(bot))
