import random
from random import Random

import discord
from discord.ext import commands, flags

from app.classes.bot import Bot
from app import converters
from app.cogs.starboard import starboard_funcs


class Fun(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @flags.add_flag('--by', type=discord.User, default=None)
    @flags.add_flag('--in', type=discord.TextChannel, default=None)
    @flags.add_flag(
        '--starboard', '--sb',
        type=converters.Starboard, default=None
    )
    @flags.add_flag('--points', type=int, default=0)
    @flags.command(
        name='random', aliases=['explore', 'rand'],
        brief="Shows a random starred message from the server"
    )
    @commands.guild_only()
    async def random_message(self, ctx: commands.Context, **options):
        author_id = options['by'].id if options['by'] else None
        channel_id = options['in'].id if options['in'] else None
        starboard_id = options['starboard'].id if options['starboard']\
            else None
        good_messages = await self.bot.db.fetch(
            """SELECT * FROM starboard_messages
            WHERE ($1::numeric is NULL or starboard_id=$1::numeric)
            AND ($2::smallint is NULL or points >= $2::smallint)
            AND EXISTS (
                SELECT * FROM messages
                WHERE id=orig_id
                AND trashed=False
                AND ($3::numeric is NULL or author_id=$3::numeric)
                AND ($4::numeric is NULL or channel_id=$4::numeric)
            )""",
            starboard_id, options['points'], author_id, channel_id
        )
        if len(good_messages) == 0:
            await ctx.send(
                "No messages were found that matched those requirements."
            )
            return
        choice = random.choice(good_messages)
        orig_sql_message = await self.bot.db.get_message(choice['orig_id'])
        sql_starboard = await self.bot.db.get_starboard(choice['starboard_id'])
        orig_message = await self.bot.cache.fetch_message(
            self.bot, ctx.guild.id, orig_sql_message['channel_id'],
            orig_sql_message['id']
        )
        if not orig_message:
            await ctx.send("Something went wrong. Please try again.")
            return

        display_emoji = sql_starboard['display_emoji']
        points = choice['points']
        channel_id = orig_sql_message['channel_id']
        forced = sql_starboard['id'] in orig_sql_message['forced']

        embed, attachments = await starboard_funcs.embed_message(
            self.bot, orig_message
        )
        plain_text = (
            f"**{display_emoji} {points} | <#{channel_id}>**"
            f"{' 🔒' if forced else ''}"
        )
        await ctx.send(plain_text, embed=embed, files=attachments)

    @commands.command(
        name='starworthy', aliases=['worthy'],
        brief="Tells you how starworthy a message is"
    )
    @commands.guild_only()
    async def starworthy(
        self, ctx: commands.Context,
        message: converters.MessageLink
    ) -> None:
        r = Random(message.id)
        worthiness: float = r.randrange(0, 100)
        await ctx.send(f"That message is {worthiness}% starworthy")


def setup(bot: Bot) -> None:
    bot.add_cog(Fun(bot))
