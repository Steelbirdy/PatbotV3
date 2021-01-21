import asyncio
from collections import deque, OrderedDict
import discord
from discord.ext import commands
from typing import Optional

from core import Context, DiscordEmojiConverter

EmojiConverter = DiscordEmojiConverter()


class Poll:
    def __init__(self, name: str, options: OrderedDict, *, timeout: float = float(60 * 60 * 12)):
        self.name = name
        self.options = options
        self.message = None
        self.bot = None
        self.timeout = timeout
        self._running = True
        self._lock = asyncio.Lock()
        self.__task = None

    async def start(self, ctx: Context, channel: discord.TextChannel = None):
        self.options = OrderedDict(
            **{await EmojiConverter.convert(ctx, emoji): text for emoji, text in self.options.items()})
        self.bot = ctx.bot
        self.message = await self.send_message(ctx, channel)
        if self.__task is not None:
            self.__task.cancel()
        self._running = True
        self.__task = self.bot.loop.create_task(self._internal_loop())

        for emoji in self.options:
            await self.message.add_reaction(emoji)

    def stop(self):
        self._running = False
        if self.__task is not None:
            self.__task.cancel()
            self.__task = None

    def reaction_check(self, payload: discord.RawReactionActionEvent) -> bool:
        if payload.user_id == self.bot.user.id:
            return False
        if payload.message_id != self.message.id:
            return False
        return payload.emoji in self.options

    async def _internal_loop(self):
        try:
            loop = self.bot.loop
            while self._running:
                tasks = [
                    asyncio.ensure_future(self.bot.wait_for('raw_reaction_add', check=self.reaction_check)),
                    asyncio.ensure_future(self.bot.wait_for('raw_reaction_remove', check=self.reaction_check)),
                ]
                done, pending = await asyncio.wait(tasks, timeout=self.timeout, return_when=asyncio.FIRST_COMPLETED)
                for task in pending:
                    task.cancel()

                if len(done) == 0:
                    raise asyncio.TimeoutError

                payload = done.pop().result()
                loop.create_task(self.update(payload))
        except asyncio.TimeoutError:
            await self.on_timeout()

    async def update(self, payload: discord.RawReactionActionEvent):
        async with self._lock:
            if self._running:
                if payload.event_type == 'REACTION_ADD':
                    do_update = await self.on_reaction_add(payload)
                elif payload.event_type == 'REACTION_REMOVE':
                    do_update = await self.on_reaction_remove(payload)
                else:
                    raise ValueError
                if do_update is not False:
                    await self.update_message()

    async def send_message(self, ctx: Context, channel: discord.TextChannel) -> discord.Message:
        raise NotImplementedError

    async def update_message(self):
        raise NotImplementedError

    async def on_reaction_add(self, payload: discord.RawReactionActionEvent) -> Optional[bool]:
        raise NotImplementedError

    async def on_reaction_remove(self, payload: discord.RawReactionActionEvent) -> Optional[bool]:
        raise NotImplementedError

    async def on_timeout(self) -> None:
        raise NotImplementedError


class SimpleStaticPoll(Poll):
    """Does not update poll display when a vote is received"""

    def __init__(self, name: str, options: OrderedDict, **kwargs):
        super(SimpleStaticPoll, self).__init__(name, options, **kwargs)
        self.embed: Optional[discord.Embed] = None
        self._author_id = None

    async def send_message(self, ctx: Context, channel: discord.TextChannel) -> discord.Message:
        self._author_id = ctx.author.id
        embed = await ctx.default_embed(title=self.name)
        if ctx.author.avatar_url:
            embed.set_author(name=f'Started by {ctx.author.display_name}', icon_url=ctx.author.avatar_url)
        else:
            embed.set_author(name=f'Started by {ctx.author.display_name}')
        for emoji, text in self.options.items():
            embed.add_field(name=str(emoji), value=text, inline=False)

        if channel is None or channel == ctx.channel:
            return await ctx.send(embed=embed)
        else:
            return await channel.send(embed=embed)

    async def update_message(self):
        pass

    async def on_reaction_add(self, payload: discord.RawReactionActionEvent) -> Optional[bool]:
        pass

    async def on_reaction_remove(self, payload: discord.RawReactionActionEvent) -> Optional[bool]:
        pass

    async def on_timeout(self) -> None:
        self.embed.title = f'[CLOSED] {self.embed.title}'
        await self.message.edit(embed=self.embed)


class SimpleDynamicPoll(Poll):
    """Updates poll display when a vote is received"""

    def __init__(self, name: str, options: OrderedDict, **kwargs):
        super(SimpleDynamicPoll, self).__init__(name, options, **kwargs)
        self.embed: Optional[discord.Embed] = None
        self._author_id = None
        self.votes = {str(emoji): 0 for emoji in self.options}
        self.voters = {}

    async def create_embed(self, ctx: Context, channel: discord.TextChannel) -> discord.Embed:
        embed = await ctx.default_embed(title=self.name)
        if ctx.author.avatar_url:
            embed.set_author(name=f'Started by {ctx.author.display_name}', icon_url=ctx.author.avatar_url)
        else:
            embed.set_author(name=f'Started by {ctx.author.display_name}')
        for emoji, text in self.options.items():
            embed.add_field(name=f'{emoji} ({text})', value='0', inline=False)
        return embed

    async def send_message(self, ctx: Context, channel: discord.TextChannel) -> discord.Message:
        self._author_id = ctx.author.id
        embed = self.embed = await self.create_embed(ctx, channel)
        if channel is None or channel == ctx.channel:
            return await ctx.send(embed=embed)
        else:
            return await channel.send(embed=embed)

    async def update_message(self):
        for i, (emoji, text) in enumerate(self.options.items()):
            self.embed.set_field_at(i, name=f'{emoji} ({text})', value=str(self.votes[str(emoji)]), inline=False)
        await self.message.edit(embed=self.embed)

    async def on_reaction_add(self, payload: discord.RawReactionActionEvent) -> Optional[bool]:
        user_id = payload.user_id
        emoji = payload.emoji
        if user_id in self.voters:
            await self.message.remove_reaction(self.voters[user_id], self.bot.get_user(user_id))
            self.votes[self.voters[user_id]] -= 1
        self.votes[str(emoji)] += 1
        self.voters[user_id] = str(emoji)
        return True

    async def on_reaction_remove(self, payload: discord.RawReactionActionEvent) -> Optional[bool]:
        user_id = payload.user_id
        if self.voters[user_id] == str(payload.emoji):
            self.votes[str(payload.emoji)] -= 1
            del self.voters[user_id]
        return True

    async def on_timeout(self) -> None:
        self.embed.title = f'[CLOSED] {self.embed.title}'
        await self.message.edit(embed=self.embed)


class AnonymousDynamicPoll(SimpleDynamicPoll):
    def __init__(self, *args, **kwargs):
        super(AnonymousDynamicPoll, self).__init__(*args, **kwargs)

    async def create_embed(self, ctx: Context, channel: discord.TextChannel) -> discord.Embed:
        embed = await super(AnonymousDynamicPoll, self).create_embed(ctx, channel)
        embed.set_footer(text='This poll is anonymous. To remove your vote, choose the same option again.')
        return embed

    async def on_reaction_add(self, payload: discord.RawReactionActionEvent) -> Optional[bool]:
        user_id = payload.user_id
        emoji = payload.emoji
        if user_id in self.voters and self.voters[user_id] == str(emoji):
            self.votes[self.voters[user_id]] -= 1
            del self.voters[user_id]
        else:
            if user_id in self.voters:
                self.votes[self.voters[user_id]] -= 1
            self.votes[str(emoji)] += 1
            self.voters[user_id] = str(emoji)
        return await self.message.remove_reaction(str(emoji), self.bot.get_user(user_id))

    async def on_reaction_remove(self, payload: discord.RawReactionActionEvent) -> Optional[bool]:
        pass
