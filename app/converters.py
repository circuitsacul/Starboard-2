from discord.ext import commands
from . import errors


class Bool(commands.Converter):
    async def convert(
        self,
        ctx: commands.Context,
        arg: str
    ) -> bool:
        yes = [
            'y', 'yes', 'on', 'enabled', 'enable', 'true', 't'
        ]
        no = [
            'n', 'no', 'off', 'disabled', 'disable', 'false', 'f'
        ]

        if arg.lower() in yes:
            return True
        elif arg.lower() in no:
            return False
        raise errors.ConversionError(
            f"I couldn't interpret `{arg}` as yes or no. Please "
            "pass one of 'yes', 'no', 'true', or 'false'."
        )


class Number(commands.Converter):
    async def convert(
        self,
        ctx: commands.Context,
        arg: str
    ) -> int:
        try:
            result = int(arg)
            return result
        except ValueError:
            raise errors.ConversionError(
                f"I couldn't interpret {arg} as an integer (number). "
                "Please pass something like `10` or `2`"
            )


class FloatingNumber(commands.Converter):
    async def convert(
        self,
        ctx: commands.Context,
        arg: str
    ) -> float:
        try:
            result = float(arg)
            return result
        except ValueError:
            raise errors.ConversionError(
                f"I couldn't interpret {arg} as a floating-point "
                "number. Please pass something like `10.9` or `6`."
            )
