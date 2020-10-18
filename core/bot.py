import asyncio
from datetime import datetime
import discord
from discord.ext import commands
from pathlib import Path
import sys

from core.config import Config
from core.context import Context


class Patbot(commands.AutoShardedBot):
    def __init__(self, auth, **options):
        self.config = Config.core_config()
        ext_to_preload = {'core', 'cogmanager', 'settings', *options.get('preload_extensions', [])}

        async def command_prefix(bot, message: discord.Message):
            # TODO: Use caching with a prefix manager
            prefixes = await self.config.from_ctx(message, 'prefixes')
            return commands.when_mentioned_or(*prefixes)(bot, message)

        options['command_prefix'] = command_prefix
        if 'owner_id' in options:
            del options['owner_id']
        options['owner_ids'] = [auth['creator_id'], *auth['co_owner_ids']]
        options['intents'] = discord.Intents.default()

        # Register auth values in the config
        self.config.register_global(
            creator_id=auth['creator_id'],
            co_owner_ids=auth['co_owner_ids']
        )

        self.__version__ = 'Not yet loaded'

        super(Patbot, self).__init__(**options)

        # Preload extensions as necessary
        for ext in ext_to_preload:
            self.load_cog(ext)

        # Record boot time
        self.last_boot = datetime.now()

    async def on_ready(self):
        self.__version__ = '.'.join(map(str, await self.config.version()))
        await self.change_presence(status=discord.Status.dnd, activity=discord.Game('Patbot testing'))

    async def shutdown(self):
        await self.logout()
        for task in asyncio.Task.all_tasks():
            try:
                task.cancel()
            except Exception:
                continue
        self.loop.stop()
        self.loop.close()
        sys.exit(3)

    async def get_context(self, message, *, cls=Context):
        return await super(Patbot, self).get_context(message, cls=cls)

    async def command_enabled_in_context(self, ctx: Context):
        return True  # TODO

    async def process_commands(self, message: discord.Message):
        if message.author.bot:
            return
        ctx = await self.get_context(message)
        if ctx.valid is True and await self.command_enabled_in_context(ctx):
            await self.invoke(ctx)
        elif ctx is None or ctx.valid is False:
            self.dispatch('message_without_command', message)

    async def accepts_embeds(self, ctx: commands.Context):
        return await self.config.from_ctx(ctx, 'accepts_embeds')

    async def embed_color(self, ctx: commands.Context):
        color = await self.config.from_ctx(ctx, 'embed_color')
        return discord.Color(int(color, base=16))

    @staticmethod
    def _format_cog_name(name: str):
        return name.lower().replace(' ', '')

    def load_cog(self, name: str):
        name = self._format_cog_name(name)
        return super(Patbot, self).load_extension(f'cogs.{name}.cog')

    def reload_cog(self, name: str):
        print(name)
        return super(Patbot, self).reload_extension(f'cogs.{name}.cog')

    def unload_cog(self, name: str):
        name = self._format_cog_name(name)
        return super(Patbot, self).unload_extension(f'cogs.{name}.cog')
