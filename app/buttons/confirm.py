from typing import TYPE_CHECKING

import discord
from discord_components import Context, InteractionType
from discord_components.button import ButtonStyle

from app.i18n import t_

from .buttons import Button, ButtonMenu, button

if TYPE_CHECKING:
    from app.classes.context import MyContext


class Confirm(ButtonMenu):
    def __init__(self, ctx: "MyContext", text: str):
        super().__init__(
            ctx.bot,
            ctx.channel,
            ctx.author.id,
            60,
            False,
        )
        self.result = None
        self.text = text

    async def start(self):
        await super().start()
        try:
            await self.message.delete()
        except discord.NotFound:
            pass
        return self.result

    async def send_initial_message(self):
        return await self.destination.send(
            self.text, components=self.buttons_list
        )

    @button(Button(label=t_("No", True), style=ButtonStyle.red), pos=1)
    async def set_no(self, ctx: Context):
        self.result = False
        self.running = False
        await ctx.respond(type=InteractionType.DeferredUpdateMessage)

    @button(Button(label=t_("Yes", True), style=ButtonStyle.green), pos=0)
    async def set_yes(self, ctx: Context):
        self.result = True
        self.running = False
        await ctx.respond(type=InteractionType.DeferredUpdateMessage)
