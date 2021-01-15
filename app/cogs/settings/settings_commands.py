import discord
from discord.ext import commands, flags

from app import errors, utils
from app.classes.bot import Bot


class Settings(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.group(
        name='prefixes', aliases=['pfx', 'prefix', 'p'],
        brief="List and manage prefixes",
        invoke_without_command=True
    )
    @commands.has_guild_permissions(manage_messages=True)
    async def prefixes(self, ctx: commands.Context) -> None:
        guild = await self.bot.db.get_guild(ctx.guild.id)
        embed = discord.Embed(
            title=f"Prefixes for {ctx.guild.name}",
            description=(
                f"{self.bot.user.mention}\n"
                + '\n'.join(f"`{p}`" for p in guild['prefixes'])
            ),
            color=self.bot.theme_color
        )
        await ctx.send(embed=embed)

    @flags.add_flag('--space', action="store_true")
    @prefixes.command(
        cls=flags.FlagCommand,
        name='add', aliases=['a'],
        brief="Adds a prefix"
    )
    @commands.has_guild_permissions(manage_messages=True)
    async def add_prefix(
        self,
        ctx: commands.Context,
        prefix: str,
        **options
    ) -> None:
        if options['space'] is True:
            prefix += ' '
        if len(prefix) > 8:
            raise discord.InvalidArgument(
                f"`{prefix}` is too long (max length is 8 characters)."
            )
        guild = await self.bot.db.get_guild(ctx.guild.id)
        if prefix in guild['prefixes']:
            raise errors.AlreadyExists(
                f"`{prefix}` is already a prefix."
            )
        new_prefixes = guild['prefixes'] + [prefix]
        await self.bot.db.execute(
            """UPDATE guilds
            SET prefixes=$1
            WHERE id=$2""", new_prefixes, ctx.guild.id
        )

        await ctx.send(f"Added `{prefix}` to the prefixes.")

    @prefixes.command(
        name='remove', aliases=['rm', 'r'],
        brief="Removes a prefix"
    )
    @commands.has_guild_permissions(manage_messages=True)
    async def remove_prefix(
        self,
        ctx: commands.Context,
        prefix: str
    ) -> None:
        to_remove = prefix
        guild = await self.bot.db.get_guild(ctx.guild.id)
        if prefix not in guild['prefixes']:
            matches = 0
            match = None
            for p in guild['prefixes']:
                if p.startswith(prefix):
                    matches += 1
                    match = p
            if matches > 1:
                raise discord.InvalidArgument(
                    f"I found {matches} matches for `{prefix}`. "
                    "Please be more specific."
                )
            elif not match:
                raise errors.DoesNotExist(
                    f"No matches found for `{prefix}`"
                )
            else:
                await ctx.send(
                    f"Did you want to remove `{match}` "
                    "from the prefixes?"
                )
                if not await utils.confirm(ctx):
                    await ctx.send("Cancelled")
                    return
                to_remove = match
        new_prefixes = guild['prefixes']
        new_prefixes.remove(to_remove)

        await self.bot.db.execute(
            """UPDATE guilds
            SET prefixes=$1
            WHERE id=$2""", new_prefixes, ctx.guild.id
        )

        await ctx.send(f"Removed `{to_remove}` from the prefixes.")

    @prefixes.command(
        name="reset",
        brief="Removes all prefixes and adds \"sb!\""
    )
    @commands.has_guild_permissions(manage_messages=True)
    async def reset_prefixes(self, ctx: commands.Context) -> None:
        await ctx.send("Are you sure you want to reset prefixes?")
        if not await utils.confirm(ctx):
            await ctx.send("Cancelled")
            return
        await self.bot.db.execute(
            """UPDATE guilds
            SET prefixes='{"sb!"}'
            WHERE id=$1""", ctx.guild.id
        )
        await ctx.send("Cleared all prefixes and added `sb!`.")


def setup(bot: Bot) -> None:
    bot.add_cog(Settings(bot))
