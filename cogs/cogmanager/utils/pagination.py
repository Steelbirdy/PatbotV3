import asyncio
import discord
from discord.ext import commands, menus
from typing import Sequence

from core import Context
from cogs.cogmanager.utils.formatting import autoformat_cog


async def get_cogs_list(ctx: Context, only_enabled: bool):
    return [c async for c in cogs_iterator(ctx, only_enabled)]


async def cogs_iterator(ctx: Context, only_enabled: bool):
    show_hidden = await ctx.bot.is_owner(ctx.author)
    for cog in ctx.bot.cogs:
        settings = cog.config.cog_settings
        visible = show_hidden or not await settings.hidden()
        enabled = not only_enabled or (await settings.enabled() and
                                       (not ctx.guild or await cog.config.guild(ctx).enabled()))
        if visible and enabled:
            yield cog


class CogPaginationSource(menus.ListPageSource):
    def __init__(self, ctx: Context, only_enabled: bool = False):
        self._ctx = ctx
        self._only_enabled = only_enabled
        data = asyncio.get_running_loop().run_until_complete(get_cogs_list(ctx, only_enabled))
        super(CogPaginationSource, self).__init__(data, per_page=1)

    async def format_page(self, menu: menus.MenuPages, entries: Sequence[commands.Cog]):
        return autoformat_cog(self._ctx, entries[0], current_page=menu.current_page, max_pages=self.get_max_pages())
