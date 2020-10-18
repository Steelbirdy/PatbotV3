import discord
from discord.ext import commands
import pathlib

from core import Config, Context, Patbot, errors
from core.formatting import *
from core import permissions as perms
from cogs.cogmanager.utils import autoformat_cog


def format_cog_name(name: str):
    return name.lower().replace(' ', '').replace('_', '')


def cog_exists(name: str):
    name = name.lower().replace(' ', '')
    pth = pathlib.Path(f'./cogs/{name}')
    return pth.exists()


async def cog_is_visible(name: str):
    if not cog_exists(name):
        return False
    return not await Config.get_config(format_cog_name(name)).cog_settings.hidden()


class CogManager(commands.Cog, name='Cog Manager'):
    """Allows global or server-wide management of cogs. Can also provide information about cogs and their commands."""
    def __init__(self, bot: Patbot):
        self.bot = bot
        self.config = Config.get_config(cog_instance=self)
        self._register_defaults()

    def _register_defaults(self):
        self.config.register_guild(
            enabled=True,
        )

    @perms.creator()
    @commands.group(name='cogs')
    async def _cogs(self, ctx: Context):
        """Allows control over cogs on a global or server basis."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(self._cogs)

    async def cog_command_error(self, ctx: Context, err: commands.CommandError):
        print(err.with_traceback(None))

        if isinstance(err, commands.CommandInvokeError):
            err = err.__cause__

        name = lambda x: x.name.split(".")[-2] if "." in x.name else x.name.lower().replace(" ", "")

        if isinstance(err, commands.ExtensionNotFound):
            return await ctx.send(error, f'No cog named `{name(err)}` exists!')
        elif isinstance(err, commands.ExtensionAlreadyLoaded):
            return await ctx.send(error, f'`{name(err)}` is already loaded!')
        elif isinstance(err, commands.ExtensionNotLoaded):
            return await ctx.send(error, f'`{name(err)}` is not currently loaded!')
        elif isinstance(err, errors.CogUnloadFailure):
            return await ctx.send(error, f'`{name(err)}` cannot be unloaded!')
        else:
            # Catch-all
            print(type(err))
            await ctx.send(fatal, f'An unhandled error occurred: {err}')
            raise err

    @_cogs.command(name='load')
    async def _cogs_load(self, ctx: Context, *, cog_name: str):
        """Loads a cog globally. Only accessible to the owner of the bot."""
        cog_name = format_cog_name(cog_name)
        if not cog_exists(cog_name):
            raise commands.ExtensionNotFound(cog_name)
        self.bot.load_cog(cog_name)
        await ctx.react_or_send(success, f'Successfully loaded `{cog_name}`!')

    @_cogs.command(name='unload')
    async def _cogs_unload(self, ctx: Context, *, cog_name: str):
        """Unloads a cog globally. Only accessible to the owner of the bot."""
        cog_name = format_cog_name(cog_name)
        if not cog_exists(cog_name):
            raise commands.ExtensionNotFound(cog_name)
        if not await Config.get_config(cog_name).cog_settings.allow_disable():
            raise errors.CogUnloadFailure(cog_name)
        self.bot.unload_cog(cog_name)
        await ctx.react_or_send(success, f'Successfully unloaded `{cog_name}`!')

    @_cogs.command(name='reload')
    async def _cogs_reload(self, ctx: Context, *, cog_name: str):
        """Reloads a cog globally. Only accessible to the owner of the bot."""
        cog_name = format_cog_name(cog_name)
        if not cog_exists(cog_name):
            raise commands.ExtensionNotFound(cog_name)
        if cog_name == 'Cog Manager':
            raise errors.CogUnloadFailure(cog_name)
        self.bot.reload_cog(cog_name)
        await ctx.react_or_send(success, f'Successfully reloaded `{cog_name}`!')

    @_cogs.command(name='info')
    async def _cogs_info(self, ctx: Context, *, cog_name: str):
        """Displays information about a given cog."""
        cog_name = format_cog_name(cog_name)

        print(self.bot.cogs)
        if not await cog_is_visible(cog_name):
            raise commands.ExtensionNotFound(cog_name)

        config = Config.get_config(cog_name)
        if not config:
            raise commands.ExtensionNotFound(cog_name)

        formatted = await autoformat_cog(ctx, config)
        if isinstance(formatted, discord.Embed):
            formatted.title = f':gear: {formatted.title}'
            return await ctx.send(embed=formatted)
        else:
            return await ctx.send(':gear:', formatted)


def setup(bot):
    bot.add_cog(CogManager(bot))
