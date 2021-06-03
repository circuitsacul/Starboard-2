import asyncio
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

import discord
from discord_components import Button
from discord_components import Context as ButtonContext
from discord_components.message import ComponentMessage

if TYPE_CHECKING:
    from app.classes.bot import Bot

ACTION = Callable[[ButtonContext], None]


class MenuButton:
    def __init__(self, button: Button, action: ACTION, remove: bool = True):
        self.button = button
        self.action = action
        self.remove = remove

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self.action(*args, **kwargs)


class ButtonMenu:
    def __init__(
        self,
        bot: "Bot",
        destination: discord.abc.Messageable,
        owner_id: int,
        timeout: float = 60.0,
        remove_after: bool = True,
    ):
        self.bot = bot
        self.destination = destination
        self.owner_id = owner_id
        self.running = True
        self.timeout = timeout
        self.remove_after = remove_after
        self.message: Optional[ComponentMessage] = None
        self.buttons: Dict[str, MenuButton] = {}
        self.grouped_buttons: Dict[int, List[MenuButton]] = {}

        self.timed_out = False

        button_funcs = []
        for name in dir(self):
            attr = self.__getattribute__(name)
            if not hasattr(attr, "__button_data__"):
                continue
            button_funcs.append((attr))
        button_funcs.sort(key=lambda f: f.__button_data__["pos"])

        for attr in button_funcs:
            data = attr.__button_data__
            btn: Button = data["button"]
            btn._id = str(bot.next_button_id)
            mbtn = MenuButton(btn, attr, data["remove"])
            self.buttons[btn.id] = mbtn
            self.grouped_buttons.setdefault(data["group"], []).append(mbtn)

    @property
    def buttons_list(self) -> List[List[Button]]:
        comps: List[List[Button]] = []
        for _, buttons in self.grouped_buttons.items():
            comps.append([])
            comps[-1].extend([b.button for b in buttons])
        return comps

    async def start(self):
        self.message = await self.send_initial_message()
        t = self.bot.loop.create_task(self._internal_loop())
        await t

    async def send_initial_message(self) -> discord.Message:
        raise NotImplementedError

    async def _internal_loop(self):
        def check(ctx: ButtonContext) -> bool:
            if ctx.user.id != self.owner_id:
                return False
            if ctx.component.id not in self.buttons:
                return False
            if ctx.message.id != self.message.id:
                return False
            return True

        try:
            while self.running:
                res: ButtonContext = await self.bot.wait_for(
                    "button_click", timeout=self.timeout, check=check
                )
                await self.buttons[res.component.id].action(res)
        except asyncio.TimeoutError:
            self.timed_out = True

        if self.remove_after:
            to_leave: List[List[Button]] = []
            for _, buttons in self.grouped_buttons.items():
                group = [b.button for b in buttons if not b.remove]
                if group:
                    to_leave.append(group)

            await self.message.edit(components=to_leave)


def button(
    btn: Button,
    remove: bool = True,
    group: int = 0,
    pos: int = -1,
):
    def decorator(coro: ACTION) -> ACTION:
        coro.__button_data__ = {
            "button": btn,
            "remove": remove,
            "group": group,
            "pos": pos,
        }
        return coro

    return decorator
