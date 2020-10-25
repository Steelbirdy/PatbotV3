import discord
from discord.ext import commands

from core import Config, Context, Patbot
from core.formatting import success, warning, error, fatal, info
import core.formatting as fmt
from core import permissions as perms


class Fun(commands.Cog):
    """A cog that has a bunch of fun miscellaneous commands."""
    def __init__(self, bot: Patbot):
        self.bot = bot
        self.config = Config.get_config(cog_instance=self)
        self._register_defaults()

    def _register_defaults(self):
        self.config.register_guild(
            enabled=False,
            commands={
                'test': False
            }
        )

    async def cog_command_error(self, ctx: Context, error_):
        if isinstance(error_, commands.CommandInvokeError):
            error_ = error_.original
        if isinstance(error_, commands.BotMissingPermissions):
            content = 'I need `' + fmt.format_permissions(error_.missing_perms) + '` permissions to run that command.'
            return await ctx.send(error, content)
        if isinstance(error_, commands.ArgumentParsingError):
            if ctx.invoked_subcommand is not None:
                return await ctx.send_help(ctx.invoked_subcommand)
            else:
                return await ctx.send_help(ctx.command)
        if isinstance(error_, commands.BadArgument):
            return await ctx.send(error, str(error_))
        return await ctx.send(fatal, f'An uncaught {error_.__class__.__name__} occurred: {error_}')


def setup(bot):
    bot.add_cog(Fun(bot))
