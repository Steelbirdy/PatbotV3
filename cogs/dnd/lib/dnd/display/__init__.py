import discord
import re
from typing import List

from core import Context
from core.formatting import split_text


MESSAGE_CHAR_LIMIT = 2000
EMBED_CHAR_LIMIT = 2048


FIELD_RE_MAP = {x: re.compile(rf'{{@{x} ([^}}]+)}}')
                for x in ['action', 'book', 'chance', 'condition', 'creature',
                          'd20', 'damage', 'dice', 'filter', 'hit', 'italic', 'item', 'note',
                          'race', 'scaledamage', 'scaledice', 'sense', 'skill', 'spell', 'table']
                }

EQUALS_FIELD_RE = re.compile(r'{=(\w+)}')

FIELD_FN_MAP = {
    'chance': lambda x: f'{x}%',
    'd20': lambda x: f'+{x}' if int(x) >= 0 else x,
    'dice': lambda x: x.split('|')[1] if x.count('|') == 1 else x,
    'filter': lambda x: x.split('|')[0],
    'spell': lambda x: f'*{fix_field(x)}*',
    'item': lambda x: f'*{fix_field(x)}*',
    'italic': lambda x: f'*{fix_field(x)}*'
}


def fix_field(x: str) -> str:
    parts, count = x.split('|'), x.count('|')
    if count == 2:
        return parts[-1]
    elif count in {1, 3}:
        return parts[0]
    else:
        return x


def remove_fields(s: str) -> str:
    for field, pattern in FIELD_RE_MAP.items():
        for match in pattern.finditer(s):
            s = s.replace(match[0], FIELD_FN_MAP.get(field, fix_field)(match[1]), 1)
    s = EQUALS_FIELD_RE.sub(r'{\1}', s)
    return s


def format_fields(text: str, data: dict) -> str:
    for k in data:
        if f'{{{k}}}' in text:
            text = text.format(**{k: data[k]})
    return text


class InfoObject:
    def __init__(self, data: dict):
        self.data = data

    @staticmethod
    def split_content(content: str, limit: int = MESSAGE_CHAR_LIMIT) -> list:
        ret = []
        add_to_next = False
        for block in split_text(content, limit=limit - 3):
            if add_to_next is True:
                block = '```' + block
                add_to_next = False
            if block.count('```') % 2:
                block += '```'
                add_to_next = True
            ret.append(block)
        return ret

    async def send_as_message(self, ctx: Context, message: discord.Message = None):
        contents = await self._as_message_contents(ctx)
        if message is not None:
            if len(contents) != 1:
                await message.delete()
                await ctx.send(content=contents[0])
            else:
                await message.edit(content=contents[0])
        for content in contents[1:]:
            await ctx.send(content=content)

    async def send_as_embed(self, ctx: Context, message: discord.Message = None):
        embeds = await self._as_embeds(ctx)
        if message is not None:
            await message.edit(embed=embeds[0])
            embeds = embeds[1:]
        for embed in embeds:
            await ctx.send(embed=embed)

    async def _as_markdown(self, ctx: Context):
        raise NotImplementedError

    async def _as_message_contents(self, ctx: Context) -> List[str]:
        contents = '\n'.join(await self._as_markdown(ctx))
        return InfoObject.split_content(contents, limit=MESSAGE_CHAR_LIMIT)

    async def _as_embeds(self, ctx: Context) -> List[discord.Embed]:
        name_mkd, body_mkd = await self._as_markdown(ctx)
        split_contents = InfoObject.split_content(body_mkd, limit=EMBED_CHAR_LIMIT)
        ret = [await ctx.default_embed(title=name_mkd, description=split_contents[0])]
        for content in split_contents[1:]:
            embed = await ctx.default_embed(description=content)
            embed.remove_author()
            ret.append(embed)
        return ret
