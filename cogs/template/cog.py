import discord
from discord.ext import commands

from core import Config, Context, Patbot
from core.formatting import success, warning, error, fatal, info
from core import permissions as perms


class Template(commands.Cog):
    """A template cog to use as a starting point for creating new ones. Doesn't have any commands of its own."""
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
        if isinstance(error_, commands.ArgumentParsingError):
            if ctx.invoked_subcommand is not None:
                return await ctx.send_help(ctx.invoked_subcommand)
            else:
                return await ctx.send_help(ctx.command)
        if isinstance(error_, commands.BadArgument):
            return await ctx.send(error, str(error_))
        return await ctx.send(fatal, f'An uncaught {error_.__class__.__name__} occurred: {error_}')

    @perms.creator()
    @commands.command(name="test", hidden=True)
    async def test(self, ctx: Context):
        await ctx.send(content='Test passed.')


def setup(bot):
    bot.add_cog(Template(bot))
