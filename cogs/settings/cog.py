import discord
from discord.ext import commands
from typing import Union

from core import Config, Context, Patbot
from core.formatting import humanize_list
from core.formatting import success, warning, error, fatal, format_time
from core import permissions as perms


class Settings(commands.Cog):
    """Allows global or server-wide control over Patbot's settings."""
    def __init__(self, bot: Patbot):
        self.bot = bot
        self.config = Config.get_config(cog_instance=self)
        self._register_defaults()

    def _register_defaults(self):
        self.config.register_global(
            delete_delay=0,
        )
        self.config.register_guild(
            admin_roles=[],
            mod_roles=[],
            delete_delay=0,
        )

    @commands.guild_only()
    @commands.command(name='settings')
    async def _settings(self, ctx: Context):
        """Displays Patbot's settings for the current server."""
        guild = ctx.guild
        roles = guild.roles
        botconfig = ctx.bot.config

        # Prefixes
        prefixes = humanize_list([f"`{p}`" for p in await botconfig.from_ctx(ctx, 'prefixes')])

        # Bot Administrator Roles
        admin_roles = await self.config.guild(ctx).admin_roles()
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

        # Delete delay
        delete_delay = await self.config.from_ctx(ctx, 'delete_delay')
        if delete_delay == 0:
            delete_delay = f'Never'
        else:
            delete_delay = f'`{delete_delay}` seconds'

        properties = {
            'Prefixes': (prefixes, False),
            'Admin roles': (admin_roles or 'Not set.', False),
            'Mod roles': (mod_roles or 'Not set.', False),
            'Delete Delay': (delete_delay, False)
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
        Permissions: Admin or higher, or "manage_nicknames" permissions.
        """
        try:
            await ctx.me.edit(nick=nickname)
        except discord.HTTPException as e:
            return await ctx.send(error, str(e))
        return await ctx.react_or_send(success, f'My nickname has been '
                                                f'{"reset" if nickname is None else "changed"} successfully.')

    @commands.guild_only()
    @perms.admin()
    @commands.group(name='prefix', aliases=['prefixes'])
    async def _prefix(self, ctx: Context):
        """Manage Patbot's prefixes on this server.
        Permissions: Admin or higher.

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
        Permissions: Admin or higher.

        Prefixes can be separated by spaces or commas.
        There are a couple of rules prefixes must follow:
            * The common prefixes "!" and "?" are not allowed.
            * Prefixes must not start with "#", "<", or "@".
            * Prefixes must not end with a letter.

        You may assign up to 3 prefixes per server. Note that mentioning Patbot will always work as well.
        """
        if not prefixes:
            return await ctx.send_help(self._prefix_add)
        prefixes = list(map(lambda p: p.strip(','), prefixes))

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
        """Remove one or more of this server's prefixes.
        Permissions: Admin or higher.

        Prefixes can be separated by spaces or commas.
        If you remove all of the assigned prefixes, the default "p!" prefix will still function.
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

    @commands.guild_only()
    @perms.guildowner()
    @commands.group(name='admin', aliases=['admins'])
    async def _admin(self, ctx: Context):
        """Manage which roles are marked as Patbot Administrator roles on this server.
        Permissions: Server owner only.

        Roles named "admin" or "administrator" are always Patbot Admin roles (case-insensitive).
        """
        if ctx.invoked_subcommand is None:
            return await ctx.send_help(self._admin)

    @_admin.command(name='add')
    async def _admin_add(self, ctx: Context, *, role: discord.Role):
        """Add a role to the list of Patbot Administrator roles on this server.
        Permissions: Server owner only.

        Roles can be referenced by name or mention (or numeric ID).
        Roles named "admin" or "administrator" are always Patbot Admin roles (case-insensitive).
        """
        async with self.config.guild(ctx).admin_roles() as current:
            current[:] = list(set(current) | {role.id})
        await ctx.react_or_send(success, 'My Admin roles on this server have been updated successfully.')

    @_admin.command(name='del', aliases=['delete', 'remove'])
    async def _admin_del(self, ctx: Context, *, role: discord.Role):
        """Remove a role from the list of Patbot Administrator roles on this server.
        Permissions: Server owner only.

        Roles can be referenced by name or mention (or numeric ID).
        Roles named "admin" or "administrator" are always Patbot Admin roles (case-insensitive).
        """
        async with self.config.guild(ctx).admin_roles() as current:
            current[:] = list(set(current) - {role.id})
        await ctx.react_or_send(success, 'My Admin roles on this server have been updated successfully.')

    @commands.guild_only()
    @perms.guildowner_or_permissions(administrator=True)
    @commands.group(name='mod', aliases=['mods'])
    async def _mod(self, ctx: Context):
        """Manage which roles are marked as Patbot Moderator roles on this server.
        Permissions: Server owner only, or users with "administrator" permissions.

        Roles named "mod" or "moderator" are always Patbot Mod roles (case-insensitive).
        """
        if ctx.invoked_subcommand is None:
            return await ctx.send_help(self._mod)

    @_mod.command(name='add')
    async def _mod_add(self, ctx: Context, *, role: discord.Role):
        """Add a role to the list of Patbot Moderator roles on this server.
        Permissions: Server owner only, or users with "administrator" permissions.

        Roles can be referenced by name or mention (or numeric ID).
        Roles named "mod" or "moderator" are always Patbot Mod roles (case-insensitive).
        """
        async with self.config.guild(ctx).mod_roles() as current:
            current[:] = list(set(current) | {role.id})
        await ctx.react_or_send(success, 'My Mod roles on this server have been updated successfully.')

    @_mod.command(name='del', aliases=['delete', 'remove'])
    async def _mod_del(self, ctx: Context, *, role: discord.Role):
        """Remove a role from the list of Patbot Moderator roles on this server.
        Permissions: Server owner only, or users with "administrator" permissions.

        Roles can be referenced by name or mention (or numeric ID).
        Roles named "mod" or "moderator" are always Patbot Mod roles (case-insensitive).
        """
        async with self.config.guild(ctx).mod_roles() as current:
            current[:] = list(set(current) - {role.id})
        await ctx.react_or_send(success, 'My Mod roles on this server have been updated successfully.')

    @commands.guild_only()
    @perms.admin_or_permissions(administrator=True)
    @commands.group(name='emoji', aliases=['emojis'])
    async def _emoji(self, ctx: Context):
        """Manage which emojis Patbot uses for different types of messages.
        Permissions: Patbot Admins only, or users with "administrator" permissions.

        Patbot has 5 customizable emojis:
            * success: Used when a command runs successfully
            * warning: Used when something dangerous is done
            * error: Used when a command fails to run
            * fatal: Used when something goes very wrong internally
            * info: Rarely used for miscellaneous information stuff
        """
        if ctx.invoked_subcommand is None:
            return await ctx.send_help(self._emoji)

    @_emoji.command(name='set')
    async def _emoji_set(self, ctx: Context, emoji_name: str, emoji: Union[discord.Emoji, str]):
        """Set an emoji Patbot uses for different types of messages.
        Permissions: Patbot Admins only, or users with "administrator" permissions.

        Patbot has 5 customizable emojis:
            * success: Used when a command runs successfully
            * warning: Used when something dangerous is done
            * error: Used when a command fails to run
            * fatal: Used when something goes very wrong internally
            * info: Rarely used for miscellaneous information stuff
        """
        async with ctx.bot.config.guild(ctx).emojis() as current:
            if emoji_name not in current:
                return await ctx.send_help(self._emoji)
            current[emoji_name] = str(emoji)
        await ctx.react_or_send(success, f'My {emoji_name} emoji on this server was changed successfully.')

    @_emoji.command(name='reset')
    async def _emoji_reset(self, ctx: Context, emoji_name: str):
        """Reset an emoji Patbot uses for different types of messages.
        Permissions: Patbot Admins only, or users with "administrator" permissions.

        Patbot has 5 customizable emojis:
            * success: Used when a command runs successfully
            * warning: Used when something dangerous is done
            * error: Used when a command fails to run
            * fatal: Used when something goes very wrong internally
            * info: Rarely used for miscellaneous information stuff
        """
        async with ctx.bot.config.guild(ctx).emojis() as current:
            if emoji_name not in current:
                return await ctx.send_help(self._emoji)
            current[emoji_name] = None
        await ctx.react_or_send(success, f'My {emoji_name} emoji on this server was reset successfully.')

    @commands.guild_only()
    @perms.guildowner_or_permissions(administrator=True)
    @commands.command(name='deletedelay')
    async def _deletedelay(self, ctx: Context, time: int):
        """Set the time delay before Patbot removes command messages.
        Permissions: Server owner only, or users with "administrator" permissions.

        Must be between 0 and 600 (measured in seconds).
        Set to 0 to disable this feature.
        """
        config = self.config.guild(ctx).delete_delay
        if time < 0:
            await config.set(0)
            return await ctx.send(warning, 'Input time was less than 0. Command messages will not be deleted.')
        elif time > 600:
            await config.set(600)
            return await ctx.send(warning, 'Input time was greater than 600. '
                                           'Command messages will be deleted after 10 minutes.')
        await config.set(time)
        formatted_time = format_time(time)
        return await ctx.react_or_send(success, f'Command messages will {"not " if time == 0 else ""} be deleted'
                                                f'{"" if time == 0 else f" after {formatted_time}"}.')


def setup(bot):
    bot.add_cog(Settings(bot))
