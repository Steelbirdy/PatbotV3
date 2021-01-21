import discord
from discord.ext import commands
import re
from typing import Any, Awaitable, Callable, Tuple, Type, TypeVar


__all__ = [
    'DiscordEmojiConverter',
    'CommandArgument',
]


class _ConverterMeta(type):
    _instances = {}

    def __call__(cls, convert_type):
        if convert_type in cls._instances:
            return cls._instances[convert_type]
        inst = super(_ConverterMeta, cls).__call__()
        cls._instances[convert_type] = inst
        return inst


_C = TypeVar('_C')


def get_converter(convert_fn: Callable[[Any, str], Awaitable[_C]]) -> Type[commands.Converter]:
    class PatbotConverter(commands.Converter):
        def __init__(self):
            self.convert_fn = convert_fn

        async def convert(self, ctx, argument: str) -> _C:
            return await self.convert_fn(ctx, argument)
    return PatbotConverter


__emoji_pattern = re.compile(r'<?(?P<animated>a)?:?(?P<name>[A-Za-z0-9_]+):(?P<id>[0-9]{13,21})>?')


async def _to_dpy_emoji(ctx, argument: str) -> discord.PartialEmoji:
    match = __emoji_pattern.match(argument)
    if match is not None:
        groups = match.groupdict()
        animated = bool(groups['animated'])
        emoji_id = int(groups['id'])
        name = groups['name']
        return discord.PartialEmoji(name=name, animated=animated, id=emoji_id)
    return discord.PartialEmoji(name=argument, id=None, animated=False)


async def _parse_cmd_arg(ctx, argument: str) -> Tuple[str, str]:
    if argument[0] != '-':
        raise commands.ArgumentParsingError
    argument = argument.strip('-')
    if '=' in argument:
        key, value = argument.split('=', 1)
    else:
        key, value = argument, True
    return key, value


DiscordEmojiConverter = get_converter(_to_dpy_emoji)
CommandArgument = get_converter(_parse_cmd_arg)
