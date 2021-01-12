from discord.ext import commands

from ...classes.bot import Bot
from ... import utils


class OwnerCommands(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.command(name='shutdown')
    @commands.is_owner()
    async def shutdown_bot(
        self,
        ctx: commands.Context
    ) -> None:
        await ctx.send("Are you sure?")
        if await utils.confirm(ctx):
            await ctx.send("Shutting down...")
            cmd: commands.Command = self.bot.get_command('evall')
            await ctx.invoke(cmd, body='exit(0)')
            return
        await ctx.send("Cancelled")

    @commands.command(name='restart')
    @commands.is_owner()
    async def restart_bot(
        self,
        ctx: commands.Context
    ) -> None:
        await ctx.send("Restart all clusters?")
        if await utils.confirm(ctx):
            await ctx.send("Restarting...")
            cmd: commands.Command = self.bot.get_command('evall')
            await ctx.invoke(cmd, body='await bot.logout()')
            return
        await ctx.send("Cancelled")


def setup(bot: Bot) -> None:
    bot.add_cog(OwnerCommands(bot))
