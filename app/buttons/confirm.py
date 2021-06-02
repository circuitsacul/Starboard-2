from typing import TYPE_CHECKING, List

from discord_components import Button, Context, InteractionType
from discord_components.button import ButtonStyle

from .buttons import ButtonMenu, button

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
        await self.message.delete()
        return self.result

    async def send_initial_message(self):
        comps: List[List[Button]] = []
        for _, buttons in self.grouped_buttons.items():
            comps.append([])
            comps[-1].extend([b.button for b in buttons])

        return await self.destination.send(self.text, components=comps)

    @button(Button(label="No", style=ButtonStyle.red), pos=1)
    async def set_no(self, ctx: Context):
        self.result = False
        self.running = False
        await ctx.respond(type=InteractionType.DeferredUpdateMessage)

    @button(Button(label="Yes", style=ButtonStyle.green), pos=0)
    async def set_yes(self, ctx: Context):
        self.result = True
        self.running = False
        await ctx.respond(type=InteractionType.DeferredUpdateMessage)
