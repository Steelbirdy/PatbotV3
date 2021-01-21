from discord import Embed, Message
from typing import List, Tuple

from . import utils
from core import Context


class InfoObject2:
    def __init__(self, data: dict):
        self.data = data
        self._mkd = None

    def _as_markdown(self) -> Tuple[str, str]:
        if self._mkd is None:
            self._mkd = self._name_body_markdown()
        return self._mkd

    def _name_body_markdown(self) -> Tuple[str, str]:
        raise NotImplementedError

    def _as_message_contents(self) -> List[str]:
        contents = '\n'.join(self._as_markdown())
        return utils.split_content(contents, limit=utils.MESSAGE_CHAR_LIMIT)

    async def _as_embeds(self, ctx: Context) -> List[Embed]:
        name_mkd, body_mkd = self._as_markdown()
        split_contents = utils.split_content(body_mkd, limit=utils.EMBED_CHAR_LIMIT)
        ret = [await ctx.default_embed(title=name_mkd, description=split_contents[0])]
        for section in split_contents[1:]:
            embed = await ctx.default_embed(description=section)
            embed.remove_author()
            ret.append(embed)
        return ret

    async def send_as_messages(self, ctx: Context, message: Message = None):
        contents = self._as_message_contents()
        if message is not None:
            if len(contents) != 1:
                await message.delete()
                await ctx.send(content=contents[0])
            else:
                await message.edit(content=contents[0])
        for content in contents[1:]:
            await ctx.send(content=content)

    async def send_as_embeds(self, ctx: Context, message: Message = None):
        embeds = await self._as_embeds(ctx)
        if message is not None:
            await message.edit(embed=embeds[0])
            embeds = embeds[1:]
        for embed in embeds:
            await ctx.send(embed=embed)
