import discord
from discord.ext import commands

from core import Config, Context, Patbot
from core.formatting import humanize_list
from core import permissions as perms


class Settings(commands.Cog):
    """Allows global or server-wide control over Patbot's settings."""
    def __init__(self, bot: Patbot):
        self.bot = bot
        self.config = Config.get_config(cog_instance=self)
        self._register_defaults()

    def _register_defaults(self):
        self.config.register_guild(
            enabled=True,
            admin_roles=[],
            mod_roles=[],
        )

    @commands.guild_only()
    @commands.group(name='set', invoke_without_command=True, aliases=['setting', 'settings'])
    async def _set(self, ctx: Context):
        """Displays Patbot's settings for the current server."""
        guild = ctx.guild
        roles = guild.roles
        botconfig = self.bot.config
        prefixes = humanize_list([f"`{p}`" for p in await botconfig.from_ctx(ctx, 'prefixes')])

        admin_roles = await self.config.guild(ctx).admin_roles()
        print(admin_roles)
        if admin_roles or discord.utils.find(lambda r: r.name.lower() in ('admin', 'administrator'), roles):
            admin_roles = humanize_list([f"`{r.name}`" for r in roles if
                                         r.id in admin_roles or r.name.lower() in ('admin', 'administrator')])
        mod_roles = await self.config.guild(ctx).mod_roles()
        if mod_roles or discord.utils.find(lambda r: r.name.lower() in ('mod', 'moderator'), roles):
            mod_roles = humanize_list([f"`{r.name}`" for r in roles if
                                       r.id in mod_roles or r.name.lower() in ('mod', 'moderator')])
        properties = {
            'Prefixes': prefixes,
            'Admin roles': admin_roles or 'Not set.',
            'Mod roles': mod_roles or 'Not set.',
        }
        embed = None
        content = ":gear: **Patbot's Server Settings**"
        if await ctx.accepts_embeds():
            embed = await ctx.default_embed()
            for k, v in properties.items():
                embed.add_field(name=k, value=v, inline=False)
        else:
            for k, v in properties.items():
                content += f'\n**{k}**: {v}'
        await ctx.send(content=content, embed=embed)


def setup(bot):
    bot.add_cog(Settings(bot))
