from typing import TYPE_CHECKING, List

from discord_components.button import Button

from .buttons import ButtonMenu, button

if TYPE_CHECKING:
    from app.classes.context import MyContext


class Confirm(ButtonMenu):
    def __init__(self, ctx: "MyContext", text: str):
        super().__init__(ctx.bot, ctx.channel, ctx.author.id, 60)
        self.result = None
        self.text = text

    async def start(self):
        await super().start()
        return self.result

    async def send_initial_message(self):
        comps: List[List[Button]] = []
        for _, buttons in self.grouped_buttons.items():
            comps.append([])
            comps[-1].extend([b.button for b in buttons])

        return await self.destination.send(self.text, components=comps)

    @button(Button(label="yes"))
    async def set_yes(self, ctx):
        self.result = True
        self.running = False
