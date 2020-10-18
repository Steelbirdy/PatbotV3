import discord
from discord.ext import commands

from core import Config, Context, Patbot
from core.formatting import humanize_list
from core.formatting import success, warning, error, fatal
from core import permissions as perms


class Settings(commands.Cog):
    """Allows global or server-wide control over Patbot's settings."""
    def __init__(self, bot: Patbot):
        self.bot = bot
        self.config = Config.get_config(cog_instance=self)
        self._register_defaults()

    def _register_defaults(self):
        self.config.register_guild(
            admin_roles=[],
            mod_roles=[],
            enabled=True,
        )

    async def cog_command_error(self, ctx: Context, error_):
        if isinstance(error_, commands.CommandInvokeError):
            error_ = error_.original
        if isinstance(error_, (commands.BadArgument, commands.BadBoolArgument, commands.BadUnionArgument)):
            return await ctx.send_help(ctx.command)
        return await ctx.send(fatal, f'An uncaught error occurred: {error_}')

    @commands.guild_only()
    @commands.command(name='settings')
    async def _settings(self, ctx: Context):
        """Displays Patbot's settings for the current server."""
        guild = ctx.guild
        roles = guild.roles
        botconfig = ctx.bot.config

        # Prefixes
        prefixes = humanize_list([f"`{p}`" for p in await botconfig.from_ctx(ctx, 'prefixes')], use_and=False)

        # Bot Administrator Roles
        admin_roles = await self.config.guild(ctx).admin_roles()
        print(admin_roles)
        if admin_roles or discord.utils.find(lambda r: r.name.lower() in ('admin', 'administrator'), roles):
            admin_roles = humanize_list([f"`{r.name}`" for r in roles if
                                         r.id in admin_roles or r.name.lower() in ('admin', 'administrator')])

        # Bot Moderator Roles
        mod_roles = await self.config.guild(ctx).mod_roles()
        if mod_roles or discord.utils.find(lambda r: r.name.lower() in ('mod', 'moderator'), roles):
            mod_roles = humanize_list([f"`{r.name}`" for r in roles if
                                       r.id in mod_roles or r.name.lower() in ('mod', 'moderator')])

        # Emojis
        emojis = {
            name.title(): await botconfig.from_ctx(ctx, 'emojis', name)
            for name in ('success', 'warning', 'error', 'fatal', 'info')
        }

        properties = {
            'Prefixes': (prefixes, False),
            'Admin roles': (admin_roles or 'Not set.', False),
            'Mod roles': (mod_roles or 'Not set.', False),
        }
        embed = None
        content = ":gear: **Patbot's Server Settings**"
        if await ctx.accepts_embeds():
            embed = await ctx.default_embed()
            for k, (v, inline) in properties.items():
                embed.add_field(name=k, value=v, inline=inline)
            for k, v in emojis.items():
                embed.add_field(name=k, value=v, inline=True)
            embed.set_footer(text=f"To change my settings, use `{ctx.prefix}help Settings`.")
        else:
            for k, (v, inline) in properties.items():
                content += f'\n**{k}**: {v}'
            for k, v in emojis.items():
                content += f'\n**{k} Emoji**: {v}'
            content += "\n\n*(To change my settings, use `{prefix}help Settings`)*."

        await ctx.send(content=content, embed=embed)

    @commands.bot_has_guild_permissions(change_nickname=True)
    @perms.admin_or_permissions(manage_nicknames=True)
    @commands.command(name='nick', aliases=['nickname'])
    async def _nickname(self, ctx: Context, *, nickname: str = None):
        """Manage Patbot's nickname on this server.

        Leave this blank to reset it.
        """
        await ctx.me.edit(nick=nickname)
        return await ctx.react_or_send(success, f'My nickname has been '
                                                f'{"reset" if nickname is None else "changed"} successfully.')

    @perms.admin()
    @commands.group(name='prefix', aliases=['prefixes'])
    async def _prefix(self, ctx: Context):
        """Manage Patbot's prefixes on this server.
        There are a couple of rules prefixes must follow:
            * The common prefixes "!" and "?" are not allowed.
            * Prefixes must not start with "#", "<", or "@".
            * Prefixes must not end with a letter.

        You may assign up to 3 prefixes per server. Note that mentioning Patbot will always work as well.
        """
        if ctx.invoked_subcommand is None:
            return await ctx.send_help(self._prefix)

    @_prefix.command(name='add')
    async def _prefix_add(self, ctx: Context, *prefixes: str):
        """Add one or more prefixes to the list of accepted prefixes on this server.
        Prefixes can be separated by spaces or commas.
        There are a couple of rules prefixes must follow:
            * The common prefixes "!" and "?" are not allowed.
            * Prefixes must not start with "#", "<", or "@".
            * Prefixes must not end with a letter.

        You may assign up to 3 prefixes per server. Note that mentioning Patbot will always work as well.
        """
        if not prefixes:
            return await ctx.send_help(self._prefix_add)
        prefixes = map(lambda p: p.strip(','), prefixes)

        for prefix in prefixes:
            if prefix[0] in {'#', '<', '@'}:
                return await ctx.send(error, 'Prefixes may not start with "#", "<", or "@".')
            if prefix[-1].isalpha():
                return await ctx.send(error, 'Prefixes may not end with letters.')
            if prefix in {'!', '?'}:
                return await ctx.send(error, '"!" and "?" may not be used as prefixes.')

        # So that we don't block the config for too long
        async with ctx.bot.config.guild(ctx).prefixes() as current:
            prefixes = {*current, *prefixes}
            if len(prefixes) > 3:
                return await ctx.send(error, 'You may assign up to 3 prefixes on this server.')
            else:
                current[:] = prefixes
        return await ctx.react_or_send(success, 'My prefixes have been updated successfully.')

    @_prefix.command(name='del', aliases=['delete', 'remove'])
    async def _prefix_del(self, ctx: Context, *prefixes: str):
        """Add one or more prefixes to the list of accepted prefixes on this server.
        Prefixes can be separated by spaces or commas.

        You may assign up to 3 prefixes per server. Note that mentioning Patbot will always work as well.
        """
        if not prefixes:
            return await ctx.send_help(self._prefix_del)
        prefixes = map(lambda p: p.strip(','), prefixes)

        to_clear = False
        async with ctx.bot.config.guild(ctx).prefixes() as current:
            current[:] = list(set(current) - set(prefixes))
            if len(current) == 0:
                to_clear = True
        if to_clear:
            await ctx.bot.config.guild(ctx).prefixes.clear()
        return await ctx.react_or_send(success, 'My prefixes have been updated successfully.')


def setup(bot):
    bot.add_cog(Settings(bot))
