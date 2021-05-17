import asyncio
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Optional, Union

import discord
from discord.ext import commands, menus

from app.constants import ARROW_LEFT, MISSING
from app.i18n import t_

from .confirm import Confirm
from .menu import Menu

if TYPE_CHECKING:
    from app.classes.context import MyContext


def wrap(func: Callable[[Any], Any]):
    """Make a non async function async."""

    async def predicate(*args, **kwargs) -> Any:
        return func(*args, **kwargs)

    return predicate


class WizardStep:
    def __init__(
        self,
        title: str,
        description: str,
        result_name: str,
        converter: Union[Callable[[str], Any], commands.Converter],
        default_value: Any,
        can_skip: bool,
        wizard: "Wizard",
        display_converter: Callable[[Any], Awaitable[str]],
    ):
        self.title = title
        self.description = description
        self.result_name = result_name
        self.converter = converter
        self.display_converter = display_converter
        self.can_skip = can_skip
        self.wizard = wizard

        self.default = default_value
        self.result: Any = MISSING

        self.task: asyncio.Task = None
        self.to_cleanup: set[int] = set()

    def _done_callback(self, task: asyncio.Task):
        try:
            task.result()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.wizard.bot.loop.run_until_complete(
                self.wizard.on_menu_button_error(e)
            )

    async def _send(self, message: str):
        m = await self.wizard.ctx.send(message)
        self.to_cleanup.add(m.id)
        return m

    async def cleanup(self):
        def check(m: discord.Message) -> bool:
            return m.id in self.to_cleanup

        await self.wizard.ctx.channel.purge(limit=100, check=check)

    async def _convert(self, arg: str) -> Any:
        if isinstance(self.converter, commands.Converter):
            return await self.converter.convert(self.wizard.ctx, arg)
        elif asyncio.iscoroutinefunction(self.converter):
            return await self.converter(arg)
        else:
            return self.converter(arg)

    async def _do_step(self):
        embed = await self.wizard._get_embed(self)
        if self.wizard.message:
            await self.wizard.message.edit(content="", embed=embed)
        else:
            self.wizard.message = await self.wizard.ctx.send(embed=embed)

        def check(message: discord.Message) -> bool:
            if message.author.id != self.wizard._author_id:
                return False
            if message.channel.id != self.wizard.ctx.channel.id:
                return False
            return True

        message = await self.wizard.bot.wait_for("message", check=check)
        self.to_cleanup.add(message.id)
        try:
            converted = await self._convert(message.content)
        except Exception as e:
            await self._send(e)
            return await self._do_step()
        self.result = converted
        await self.cleanup()
        await self.wizard.next_step()

    def do_step(self):
        self.task = self.wizard.bot.loop.create_task(self._do_step())
        self.task.add_done_callback(self._done_callback)

    def cancel(self):
        if self.task:
            self.task.cancel()
            self.task = None

    def skip(self):
        self.cancel()
        if self.result is MISSING:
            self.result = self.default


class Wizard(Menu):
    def __init__(
        self,
        name: str,
        description: str = "",
        done_callback: Callable[["Wizard"], Awaitable[None]] = None,
    ):
        super().__init__(delete_after=True)
        self.name = name
        self.description = description
        self.current_step = 0
        self.steps: list["WizardStep"] = []
        self.finished = False
        self.done_callback = done_callback

    @property
    def result(self) -> dict[str, Any]:
        dct = {}
        for s in self.steps:
            dct[s.result_name] = s.default if s.result is MISSING else s.result
        return dct

    def _get_missing(self, permissions: discord.Permissions) -> list[str]:
        missing: list[str] = []
        if not permissions.manage_messages:
            missing.append("Manage Messages")
        missing.extend(super()._get_missing(permissions))
        return missing

    async def confirm(self) -> bool:
        c = Confirm(t_("Does everything look good?"))
        if await c.start(self.ctx):
            return True
        return False

    def add_step(
        self,
        name: str,
        result_name: str,
        description: str,
        converter: Union[Callable[[str], Any], commands.Converter] = str,
        can_skip: bool = False,
        default: Optional[Any] = None,
        display_converter: Callable[[Any], Awaitable[str]] = wrap(str),
    ):
        self.steps.append(
            WizardStep(
                name,
                description,
                result_name,
                converter=converter,
                default_value=default,
                can_skip=can_skip,
                wizard=self,
                display_converter=display_converter,
            )
        )

    async def _get_embed(
        self, current_step: Optional["WizardStep"]
    ) -> discord.Embed:
        desc: list[str] = []
        for n, step in enumerate(self.steps, 1):
            selector = f" **{ARROW_LEFT}**" if step is current_step else ""
            presult = (
                MISSING
                if step.result is MISSING
                else await step.display_converter(step.result)
            )
            result = f" **{presult}**" if presult is not MISSING else ""
            pdefault = await step.display_converter(step.default)
            default = f" (Default {pdefault})" if step.can_skip else ""
            desc.append(f"{n}. {step.title}:{result}{default}{selector}")
        desc = "\n".join(desc)
        desc = self.description + "\n" * 2 + desc
        embed = discord.Embed(
            title=self.name,
            description=desc,
            color=self.bot.theme_color,
        )
        if current_step:
            embed.add_field(
                name=current_step.title,
                value=current_step.description,
            )

        return embed

    async def next_step(self):
        self.current_step += 1
        try:
            step = self.steps[self.current_step]
        except IndexError:
            embed = await self._get_embed(None)
            await self.message.edit(embed=embed)
            if await self.confirm():
                self.finished = True
                if self.done_callback:
                    await self.done_callback(self)
                self.stop()
            else:
                self.current_step = -1
                await self.next_step()
        else:
            step.do_step()

    async def on_menu_button_error(self, exc: Exception):
        self.steps[self.current_step].cancel()
        await self.steps[self.current_step].cleanup()
        return await super().on_menu_button_error(exc)

    async def start(self, ctx: "MyContext", *, channel=None, wait=False):
        self.message = await ctx.send("Starting...")
        await super().start(ctx, channel=channel, wait=wait)
        self.steps[0].do_step()

    @menus.button("\N{BLACK SQUARE FOR STOP}")
    async def stop_menu(self, payload: discord.RawReactionActionEvent):
        self.steps[self.current_step].cancel()
        await self.steps[self.current_step].cleanup()
        self.stop()

    @menus.button("\N{BLACK LEFT-POINTING TRIANGLE}")
    async def prev_step(self, payload: discord.RawReactionActionEvent):
        self.steps[self.current_step].cancel()
        await self.steps[self.current_step].cleanup()
        if self.current_step > 0:
            self.current_step -= 1
            self.steps[self.current_step].do_step()

    @menus.button("\N{BLACK RIGHT-POINTING TRIANGLE}")
    async def skip_step(self, payload: discord.RawReactionActionEvent):
        step = self.steps[self.current_step]
        if not step.can_skip and step.result is MISSING:
            return
        step.skip()
        await step.cleanup()
        await self.next_step()
