from typing import TYPE_CHECKING, Awaitable, Callable, Dict, List, Optional

import discord
from discord.ext import menus

from app.constants import NUMBER_EMOJIS

from .menu import Menu

if TYPE_CHECKING:
    from app.classes.context import MyContext


def new_button() -> Callable[
    ["MultipleChoice", discord.RawReactionActionEvent], Awaitable[None]
]:
    async def button_action(
        menu: "MultipleChoice", payload: discord.RawReactionActionEvent
    ):
        menu.result = menu.options[payload.emoji.name]
        menu.stop()

    return button_action


class MultipleChoice(Menu):
    def __init__(self, description: str, options: List[str]):
        super().__init__(True, timeout=30.0)

        self.description = description
        self.options: Dict[str, str] = {}
        self.result: Optional[str] = None

        for x, opt in enumerate(options):
            self.options[NUMBER_EMOJIS[x]] = opt
            self.add_button(
                menus.Button(
                    NUMBER_EMOJIS[x],
                    new_button(),
                    position=menus.Position(x + 1),
                )
            )

    async def send_initial_message(
        self, ctx: "MyContext", channel: discord.abc.Messageable
    ) -> discord.Message:
        message = f"{self.description}\n" + "\n".join(
            [f"{e}: {s}" for e, s in self.options.items()]
        )
        return await channel.send(message)

    @menus.button("\N{BLACK SQUARE FOR STOP}")
    async def cancel(self, payload: discord.RawReactionActionEvent):
        self.stop()
