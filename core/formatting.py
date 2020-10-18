import discord
from discord.ext.commands import Context
from io import BytesIO
from typing import Any, Awaitable, Callable

import core.errors as __errors

__all__ = [
    'success',
    'warning',
    'error',
    'fatal',
    'info',
]


def __emoji(emoji_name: str) -> Callable[[Context, str], Awaitable[str]]:
    async def inner(ctx: Context, text: str) -> str:
        emoji = await ctx.bot.config.from_ctx(ctx, 'emojis', emoji_name)
        if not emoji:
            raise __errors.ConfigKeyError(f'Emoji not found: {emoji_name}')
        return f'{emoji} {text.strip()}' if text else emoji
    return inner


success = __emoji('success')
warning = __emoji('warning')
error = __emoji('error')
fatal = __emoji('fatal')
info = __emoji('info')


def bold(text: str) -> str:
    return f'**{text}**'


def italic(text: str) -> str:
    return f'*{text}*'


def underline(text: str) -> str:
    return f'__{text}__'


def strikethrough(text: str) -> str:
    return f'~~{text}~~'


def block(text: str, lang: str = 'py') -> str:
    return f'```{lang}\n{text}\n```'


def inline(text: str) -> str:
    return f'`{text}`'


def escape(text: str) -> str:
    return text.replace('@here', '@h\u1077re').replace('@everyone', '@\u1077veryone')


def humanize_list(items, *, use_and: bool = True) -> str:
    items = list(map(str, items))
    if len(items) == 0:
        raise IndexError('Cannot humanize empty sequence') from None
    elif len(items) == 1:
        return items[0]
    elif not use_and:
        return ', '.join(items)
    return ', '.join(items[:-1]) + (',' if len(items) > 2 else '') + ' and ' + items[-1]


def format_permissions(permissions: discord.Permissions) -> str:
    perm_names = []
    for perm, value in permissions:
        if value is True:
            perm_names.append(f'"{perm.replace("_", " ").title()}"')
    return humanize_list(perm_names).replace('Guild', 'Server')


def format_time(seconds: int, *, compact: bool = False, use_days: bool = False) -> str:
    if compact:
        return __format_time_compact(seconds, use_days)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    tr = []
    if use_days and hours >= 24:
        days, hours = divmod(hours, 24)
        tr.append(f'{days} day{"" if days == 1 else "s"}')
    if hours:
        tr.append(f'{hours} hour{"" if hours == 1 else "s"}')
    if minutes:
        tr.append(f'{minutes} minute{"" if minutes == 1 else "s"}')
    if seconds:
        tr.append(f'{seconds} second{"" if seconds == 1 else "s"}')
    return humanize_list(tr)


def __format_time_compact(seconds: int, use_days: bool = False) -> str:
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    tr = ''
    if use_days:
        days, hours = divmod(hours, 24)
        tr = f'{str(days).zfill(2)}:'
    tr += f'{str(hours).zfill(2)}:{str(minutes).zfill(2)}:{str(seconds).zfill(2)}'
    return tr


def text_to_file(text: str, file_name: str = 'file.txt',
                 *, spoiler: bool = False, encoding: str = 'utf-8') -> discord.File:
    file = BytesIO(text.encode(encoding))
    return discord.File(file, file_name, spoiler=spoiler)
