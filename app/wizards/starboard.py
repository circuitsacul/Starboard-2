from typing import TYPE_CHECKING, Awaitable, Callable, Union

import discord
from discord.ext import commands, wizards

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
    async def convert(self, ctx: "MyContext", arg: str) -> list[str]:
        args = [a.strip() for a in arg.split()]
        set_emojis: set[str] = set()
        for arg in args:
            try:
                converted = await super().convert(ctx, arg)
            except (errors.CustomEmojiFromOtherGuild, errors.NotAnEmoji):
                continue
            else:
                set_emojis.add(converted)
        emojis: list[str] = []
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
) -> Callable[[list[Union[str, discord.Emoji]]], Awaitable[str]]:
    async def predicate(emojis: list[Union[str, discord.Emoji]]) -> str:
        return utils.pretty_emoji_string(emojis, guild)

    return predicate


def pretty_emoji_str(
    guild: discord.Guild,
) -> Callable[[Union[str, discord.Emoji]], Awaitable[str]]:
    async def predicate(emoji: Union[str, discord.Emoji]) -> str:
        return utils.pretty_emoji_string([emoji], guild)

    return predicate


class StarboardWizard(wizards.Wizard):
    @wizards.step(
        "What channel should I setup a new starboard in?", position=1
    )
    async def channel(self, step: wizards.Step, message: discord.Message):
        try:
            channel = await CanBeStarboard().convert(
                self._ctx, message.content
            )
        except Exception as e:
            await self.send(e)
            return await self.channel.do_step(self)
        else:
            step.result = channel

    @wizards.step(
        "How many stars should a message need to appear on the starboard?",
        position=2,
    )
    async def required(self, step: wizards.Step, message: discord.Message):
        try:
            value = required_stars(message.content)
        except Exception as e:
            await self.send(e)
            return await self.required.do_step(self)
        else:
            step.result = value

    @wizards.step(
        "Should users be allowed to star their own messages?",
        position=3,
    )
    async def self_star(self, step: wizards.Step, message: discord.Message):
        try:
            value = converters.mybool(message.content)
        except Exception as e:
            await self.send(e)
        else:
            step.result = value

    @wizards.step('What emojis should count as "stars"?', position=4)
    async def star_emojis(self, step: wizards.Step, message: discord.Message):
        value = await ListOfEmojis().convert(self._ctx, message.content)
        step.result = value
