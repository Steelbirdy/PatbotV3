import discord
from discord.embeds import EmptyEmbed
from discord.ext import commands
from discord.ext.commands import Context as DpyContext
import logging
from typing import Awaitable, Callable, Optional, Union

from core.formatting import success, warning, error, info


class Context(DpyContext):
    log = logging.getLogger('context')
    bot: commands.bot.BotBase
    command: commands.Command
    invoked_subcommand: Optional[commands.Command]
    me: Union[discord.ClientUser, discord.Member]

    async def send(self, flavor: Union[str, Callable[["Context", str], Awaitable[str]]] = None, content: str = None, **kwargs):
        _filter: Callable[[str], str] = kwargs.pop('filter', None)
        if content is not None:
            if flavor:
                if callable(flavor):
                    content = await flavor(self, content)
                else:
                    content = f'{flavor} {content}'
            if _filter:
                content = _filter(str(content))
            content = await self.format_content(str(content))
        return await super(Context, self).send(content=content, **kwargs)

    async def react(self, reaction: Union[discord.Emoji, discord.Reaction, discord.PartialEmoji, str]) -> bool:
        try:
            await self.message.add_reaction(reaction)
        except discord.HTTPException:
            return False
        else:
            return True

    async def safe_delete(self, *, delay: float = 0) -> bool:
        try:
            await self.message.delete(delay=delay)
        except discord.Forbidden:
            self.log.debug('Failed to delete message (insufficient permissions).')
        except discord.NotFound:
            self.log.debug('Failed to delete message (message not found).')
        except discord.HTTPException:
            self.log.debug('Failed to delete message (reason unknown).')
        else:
            return True
        return False

    async def accepts_embeds(self) -> bool:
        if self.guild and not self.channel.permissions_for(self.guild.me).embed_links:
            return False
        return await self.bot.accepts_embeds(self)

    async def default_embed(self, **kwargs) -> discord.Embed:
        title = kwargs.get('title', EmptyEmbed)
        description = kwargs.get('description', EmptyEmbed)
        color = kwargs.get('color', await self.embed_color())
        url = kwargs.get('url', EmptyEmbed)
        timestamp = kwargs.get('timestamp', EmptyEmbed)
        embed = discord.Embed(title=title, description=description, color=color,
                              url=url, timestamp=timestamp)
        embed.set_author(name=self.me.display_name, icon_url=self.me.avatar_url)
        return embed

    async def embed_color(self):
        return await self.bot.embed_color(self)

    async def format_content(self, content: str) -> str:
        return content.format(botname=self.me.display_name, prefix=self.prefix)
