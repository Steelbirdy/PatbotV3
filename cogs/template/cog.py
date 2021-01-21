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
        pass

    @perms.creator()
    @commands.command(name="test", hidden=True)
    async def test(self, ctx: Context):
        await ctx.send(content='Test passed.')


def setup(bot):
    bot.add_cog(Template(bot))
