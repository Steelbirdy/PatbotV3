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
            enabled=False
        )

    def cog_command_error(self, ctx: Context, error_):
        if isinstance(error_, commands.CommandInvokeError):
            error_ = error_.original
        if isinstance(error_, (commands.BadArgument, commands.BadBoolArgument, commands.BadUnionArgument)):
            return await ctx.send_help(ctx.command)
        return await ctx.send(fatal, f'An uncaught error occurred: {error_}')

    @perms.creator()
    @commands.command(name="test", hidden=True)
    async def test(self, ctx: Context):
        await ctx.send(content='Test passed.')


def setup(bot):
    bot.add_cog(Template(bot))
