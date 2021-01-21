import asyncio
import datetime
import discord
from discord.ext import commands
from pathlib import Path
import sys

from core.config import Config
from core.context import Context
from core import formatting as fmt


class Patbot(commands.AutoShardedBot):
    def __init__(self, auth, **options):
        self.config = Config.core_config()
        self._testing = False
        ext_to_preload = {'cogmanager', 'core', 'dnd', 'fun', 'polling', 'repl', 'settings'}

        async def command_prefix(bot, message: discord.Message):
            prefixes = await self.config.from_ctx(message, 'prefixes') or ['p!']
            return commands.when_mentioned_or(*prefixes)(bot, message)

        options['command_prefix'] = command_prefix
        if 'owner_id' in options:
            del options['owner_id']
        options['owner_ids'] = [auth['creator_id'], *auth['co_owner_ids']]
        options['intents'] = discord.Intents.default()
        options['intents'].members = True

        self.__version__ = 'Not yet loaded'

        super(Patbot, self).__init__(**options)

        # Preload extensions as necessary
        for ext in ext_to_preload:
            self.load_cog(ext)

        # Record boot time
        self.last_boot = datetime.datetime.now()

    async def on_ready(self):
        self.__version__ = '.'.join(map(str, await self.config.version()))
        if not self._testing:
            await self.change_presence(activity=discord.Game('!!help'))
        else:
            await self.change_presence(activity=discord.Game('Patbot testing'))

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
        return await super().get_context(message, cls=cls)

    async def process_commands(self, message: discord.Message):
        if not message.author.bot:
            ctx = await self.get_context(message)
            await self.invoke(ctx)
        else:
            ctx = None
        if ctx is None or ctx.valid is False:
            self.dispatch('message_without_command', message)

    async def accepts_embeds(self, ctx: commands.Context):
        return await self.config.from_ctx(ctx, 'accepts_embeds')

    async def embed_color(self, ctx: commands.Context):
        if ctx.guild:
            return ctx.me.color
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

    async def on_command_error(self, ctx: Context, exception):
        if isinstance(exception, commands.CommandInvokeError):
            exception = exception.original
        if isinstance(exception, commands.CommandNotFound):
            return
        if isinstance(exception, commands.MissingRequiredArgument):
            return await ctx.send_help(ctx.command)
        if isinstance(exception, commands.BotMissingPermissions):
            content = 'I need `' + fmt.format_permissions(exception.missing_perms) + \
                      '` permissions to run that command.'
            return await ctx.send(fmt.error, content)
        if isinstance(exception, commands.ArgumentParsingError):
            if ctx.invoked_subcommand is not None:
                return await ctx.send_help(ctx.invoked_subcommand)
            else:
                return await ctx.send_help(ctx.command)
        if isinstance(exception, commands.BadArgument):
            return await ctx.send(fmt.error, str(exception))
        await ctx.send(fmt.fatal, f'An uncaught {exception.__class__.__name__} occurred: {exception}')
        raise exception
