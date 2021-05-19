from copy import deepcopy
from typing import TYPE_CHECKING, Awaitable, Callable, List, Optional

import discord
from discord.ext import menus

from app.constants import ZWS

from .menu import Menu

if TYPE_CHECKING:
    from app.classes.context import MyContext


NUMBER_EMOJIS = [
    "1️⃣",
    "2️⃣",
    "3️⃣",
    "4️⃣",
    "5️⃣",
    "6️⃣",
    "7️⃣",
    "8️⃣",
    "9️⃣",
    "🔟",
]


class _AccordionField:
    def __init__(self, accordion: "Accordion", name: str, value: str):
        self.name = name
        self.value = value
        self._accordion = accordion
        self.embed: Optional[discord.Embed] = None

    async def _set_to(self):
        if not self.embed:
            embed: discord.Embed = deepcopy(self._accordion._embed)
            embed.clear_fields()
            for field in self._accordion.fields:
                if field is self:
                    value = self.value
                else:
                    value = ZWS
                embed.add_field(name=field.name, value=value, inline=False)
            self.embed = embed

        await self._accordion.message.edit(embed=self.embed)


class Accordion(Menu):
    def __init__(self, embed: discord.Embed):
        super().__init__(delete_after=True)
        self._embed = embed
        self._embed.clear_fields()
        self.fields: List["_AccordionField"] = []

        self._buttons = {}

    async def start(self, ctx, *, channel=None, wait=False):
        self.set_buttons()
        return await super().start(ctx, channel=channel, wait=wait)

    async def send_initial_message(
        self, ctx: "MyContext", destination: discord.abc.Messageable
    ):
        for field in self.fields:
            self._embed.add_field(name=field.name, value=ZWS, inline=False)
        return await destination.send(embed=self._embed)

    @staticmethod
    def _set_field(
        field: "_AccordionField",
    ) -> Callable[
        ["Accordion", discord.RawReactionActionEvent], Awaitable[None]
    ]:
        async def set_field(
            menu: "Accordion", payload: discord.RawReactionActionEvent
        ):
            await field._set_to()

        return set_field

    def set_buttons(self):
        for num, field in enumerate(self.fields):
            emoji = NUMBER_EMOJIS[num]
            field.name = f"{emoji} {field.name}"
            self._buttons[emoji] = menus.Button(
                emoji,
                self._set_field(field),
            )
        self._buttons["\N{BLACK SQUARE FOR STOP}"] = menus.Button(
            "\N{BLACK SQUARE FOR STOP}", self.astop
        )

    async def astop(self, payload):
        return self.stop()

    def add_field(self, name: str, value: str) -> "Accordion":
        self.fields.append(_AccordionField(self, name, value))
        return self
