from typing import TYPE_CHECKING, Awaitable, Callable, List, Union

import discord
from discord.ext import commands, wizards
from discord.ext.wizards.stopreason import StopReason

from app import converters, errors, utils
from app.i18n import t_

if TYPE_CHECKING:
    from app.classes.context import MyContext


class CanBeStarboard(commands.TextChannelConverter):
    async def convert(self, ctx: "MyContext", arg: str) -> discord.TextChannel:
        obj = await super().convert(ctx, arg)
        exists = await ctx.bot.db.starboards.get(obj.id)
        if exists:
            raise errors.AlreadyStarboard(obj.mention)
        is_asc = await ctx.bot.db.aschannels.get(obj.id)
        if is_asc:
            raise errors.CannotBeStarboardAndAutostar()
        return obj


class ListOfEmojis(converters.Emoji):
    async def convert(self, ctx: "MyContext", arg: str) -> List[str]:
        args = [a.strip() for a in arg.split()]
        set_emojis: set[str] = set()
        for arg in args:
            try:
                converted = await super().convert(ctx, arg)
            except (errors.CustomEmojiFromOtherGuild, errors.NotAnEmoji):
                continue
            else:
                set_emojis.add(converted)
        emojis: List[str] = []
        for e in set_emojis:
            if isinstance(e, discord.Emoji):
                emojis.append(str(e.id))
            else:
                emojis.append(e)
        return emojis


class Emoji(converters.Emoji):
    async def convert(self, ctx: "MyContext", arg: str) -> str:
        result = await super().convert(ctx, arg)
        if isinstance(result, discord.Emoji):
            return str(result.id)
        return result


def required_stars(arg: str) -> int:
    num = converters.myint(arg)
    if num < 1:
        raise commands.BadArgument(t_("requiredStars cannot be less than 1."))
    elif num > 500:
        raise commands.BadArgument(
            t_("requiredStars cannot be greater than 500.")
        )
    return num


def pretty_emoji_str_list(
    guild: discord.Guild,
) -> Callable[[List[Union[str, discord.Emoji]]], Awaitable[str]]:
    async def predicate(emojis: List[Union[str, discord.Emoji]]) -> str:
        return utils.pretty_emoji_string(emojis, guild)

    return predicate


def pretty_emoji_str(
    guild: discord.Guild,
) -> Callable[[Union[str, discord.Emoji]], Awaitable[str]]:
    async def predicate(emoji: Union[str, discord.Emoji]) -> str:
        return utils.pretty_emoji_string([emoji], guild)

    return predicate


class StarboardWizard(wizards.Wizard):
    async def on_step_error(self, step: wizards.Step, err: Exception):
        await self.send(err)
        return await step.do_step(self)

    @wizards.action("cancel")
    async def cancel_wizard(self, message: discord.Message):
        await self.stop(StopReason.CANCELLED)

    @wizards.step(
        "Do you want to (1) create a new channel or (2) use an "
        "existing channel?",
        name="channel",
        position=1,
    )
    async def create_or_use(
        self, step: wizards.Step, message: discord.Message
    ):
        if message.content == "1":
            result = await self.create_channel.do_step(self)
            if result is None:
                await self.send("I don't have permission to create channels.")
                return await step.do_step(self)
            else:
                step.result = result
        elif message.content == "2":
            step.result = await self.use_channel.do_step(self)
        else:
            await self.send("Please choose 1 or 2.")
            return await step.do_step(self)

    @wizards.step(
        "What channel should I setup a new starboard in?",
        call_internally=False,
    )
    async def use_channel(
        self, step: wizards.Step, message: discord.Message
    ) -> discord.TextChannel:
        return await CanBeStarboard().convert(self._ctx, message.content)

    @wizards.step(
        "What should the channel be named?",
        call_internally=False,
    )
    async def create_channel(
        self,
        step: wizards.Step,
        message: discord.Message,
    ) -> discord.TextChannel:
        try:
            return await self._ctx.guild.create_text_channel(message.content)
        except discord.Forbidden:
            return None

    @wizards.step(
        "How many stars should a message need to appear on the starboard?",
        position=2,
    )
    async def required(self, step: wizards.Step, message: discord.Message):
        step.result = required_stars(message.content)

    @wizards.step(
        "Should users be allowed to star their own messages?",
        position=3,
    )
    async def self_star(self, step: wizards.Step, message: discord.Message):
        step.result = converters.mybool(message.content)

    @wizards.step('What emojis should count as "stars"?', position=4)
    async def star_emojis(self, step: wizards.Step, message: discord.Message):
        step.result = await ListOfEmojis().convert(self._ctx, message.content)
