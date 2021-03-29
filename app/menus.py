from typing import Optional

import discord
from discord.ext import menus, commands


class Confirm(menus.Menu):
    def __init__(self, message: str) -> None:
        super().__init__(timeout=30, delete_message_after=True)
        self.msg = message
        self.result = None

    async def send_initial_message(
        self, ctx: commands.Context, channel: discord.TextChannel
    ) -> discord.Message:
        return await channel.send(self.msg)

    @menus.button("\N{WHITE HEAVY CHECK MARK}")
    async def confirm(self, payload: discord.RawReactionActionEvent) -> None:
        self.result = True
        self.stop()

    @menus.button("\N{CROSS MARK}")
    async def deny(self, payload: discord.RawReactionActionEvent) -> None:
        self.result = False
        self.stop()

    async def start(self, ctx: commands.Context) -> Optional[bool]:
        await super().start(ctx, wait=True)
        return self.result
