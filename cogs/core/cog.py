import discord
from discord.ext import commands, menus
import getpass
import os
import pip
import platform
import sys
import time

from core import Config, Context, menus, Patbot
from core import formatting as fmt
from core import permissions as perms


class Core(commands.Cog):
    """Allows control over core functionality of the bot, and allows servers to customize their experience."""

    def __init__(self, bot: Patbot):
        self.bot = bot
        self.config = Config.core_config()
        self._register_defaults()

    def _register_defaults(self):
        self.config.register_global(
            prefixes=['p!'],
            emojis={
                'success': '\N{OK Hand Sign}',
                'warning': '\N{Warning Sign}',
                'error': '\N{No Entry Sign}',
                'fatal': '\N{Skull}',
                'info': '\N{Information Source}',
            },
            accepts_embeds=True,
            embed_color=hex(discord.Color.blurple().value),
        )
        self.config.register_guild(
            prefixes=['p!'],
            emojis={
                'success': '\N{OK Hand Sign}',
                'warning': '\N{Warning Sign}',
                'error': '\N{No Entry Sign}',
                'fatal': '\N{Skull}',
                'info': '\N{Information Source}',
            },
            accepts_embeds=True,
            embed_color=hex(discord.Color.blurple().value),
            enabled=True,
            commands={
                'shutdown': True,
                'ping': True,
                'invite': True,
                'botserver': True,
                'about': True,
                'debuginfo': True,
                'contact': True,
                'dm': True,
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
            return await ctx.send(fmt.error, str(error_))
        return await ctx.send(fmt.fatal, f'An uncaught {error_.__class__.__name__} occurred: {error_}')

    @perms.owner()
    @commands.command(name='shutdown')
    async def _shutdown(self, ctx: Context, *, confirm: bool = False):
        """Shut down Patbot.

        Optionally, you can provide a confirmation word (ex. 'yes', 'true', etc.)
        to bypass the confirmation menu that comes up.
        """
        if not confirm:
            confirm = await menus.Confirm(await fmt.warning(ctx, 'Are you sure you want me to shut down?')).prompt(ctx)
        if confirm:
            await ctx.send(':wave:', 'Shutting down...')
            await self.bot.shutdown()

    @_shutdown.error
    async def _shutdown_error(self, ctx: Context, err: commands.CommandError):
        if isinstance(err, commands.BadBoolArgument):
            return await ctx.invoke(self._shutdown)

    @commands.command(name='ping')
    async def _ping(self, ctx: Context):
        """Pong!"""
        before = time.monotonic()
        before_ws = int(round(self.bot.latency * 1000, 1))
        message = await ctx.send(content=':ping_pong: Pong!')
        ping = (time.monotonic() - before) * 1000
        await message.edit(content=f':ping_pong: Ping: {int(ping)}ms  |  Websocket: {before_ws}ms')

    @commands.command(name='invite', aliases=['botinvite', 'invitelink'])
    async def _invite(self, ctx: Context):
        """Invite Patbot to your server!"""
        await ctx.send(content=f'**{ctx.author.display_name}**, use this URL to invite me to your server:\n'
                               f'<{discord.utils.oauth_url(ctx.me.id)}>')

    @commands.command(name='botserver', aliases=['supportserver', 'feedbackserver'])
    async def _botserver(self, ctx: Context):
        """Get an invite to Patbot's support server!"""
        if not ctx.guild or ctx.guild.id != 765314921151332464:
            return await ctx.send(content=f'Here you go **{ctx.author.display_name}** :tada:\n'
                                          f'https://discord.gg/r6KXeYy')
        else:
            return await ctx.react_or_send(fmt.error, "This command shouldn't be used on my support server.")

    @commands.command(name='about', aliases=['info'])
    async def _about(self, ctx: Context):  # TODO: Wrap in info()
        """About Patbot."""
        properties = {
            'Version': self.bot.__version__,
            'Last boot': self.bot.last_boot.strftime("%B %d, %Y @ %I:%M%p"),
            'Developer': 'Steelbirdy#3536',
            'Library': 'discord.py',
            '# of cogs': len(self.bot.cogs),
            '# of commands': len(self.bot.commands)
        }
        content = 'About **{botname}**'

        if await ctx.accepts_embeds():
            embed = await ctx.default_embed()
            for k, v in properties.items():
                embed.add_field(name=k, value=v, inline=False)
            embed.set_thumbnail(url=ctx.me.avatar_url)
            await ctx.send(embed=embed)
        else:
            for k, v in properties.items():
                content += f'\n  **{k}**: {v}'
            await ctx.send(content=content)

    @perms.creator()
    @commands.command(name='debuginfo')
    async def _debuginfo(self, ctx: Context):
        """Shows useful debug info.
        Permissions: Bot owner only.
        """
        if sys.platform == 'linux':
            import distro

        IS_WINDOWS = os.name == 'nt'
        IS_MAC = sys.platform == 'darwin'
        IS_LINUX = sys.platform == 'linux'

        pyver = '{}.{}.{} ({})'.format(*sys.version_info[:3], platform.architecture()[0])
        pipver = pip.__version__
        patbotver = self.bot.__version__
        dpy_version = discord.__version__
        if IS_WINDOWS:
            os_info = platform.uname()
            osver = '{} {} (version {})'.format(os_info.system, os_info.release, os_info.version)
        elif IS_MAC:
            os_info = platform.mac_ver()
            osver = 'MacOS {} {}'.format(os_info[0], os_info[2])
        elif IS_LINUX:
            os_info = distro.linux_distribution()
            osver = '{} {}'.format(os_info[0], os_info[1]).strip()
        else:
            osver = 'Could not parse OS.'
        user_who_ran = getpass.getuser()
        driver = 'JSON'

        if await ctx.accepts_embeds():
            e = discord.Embed(color=await ctx.embed_color())
            e.title = 'Debug Info for Patbot'
            e.add_field(name='Patbot version', value=patbotver, inline=True)
            e.add_field(name='Python version', value=pyver, inline=True)
            e.add_field(name='Discord.py version', value=dpy_version, inline=True)
            e.add_field(name='Pip version', value=pipver, inline=True)
            e.add_field(name='System arch', value=platform.machine(), inline=True)
            e.add_field(name='User', value=user_who_ran, inline=True)
            e.add_field(name='OS version', value=osver, inline=False)
            e.add_field(
                name='Python executable',
                value=discord.utils.escape_markdown(sys.executable),
                inline=False
            )
            e.add_field(name='Storage type', value=driver, inline=False)
            await ctx.send(embed=e)
        else:
            _info = (
                'Debug Info for Patbot\n\n'
                f'Patbot version: {patbotver}\n'
                f'Python version: {pyver}\n'
                f'Python executable: {sys.executable}\n'
                f'Discord.py version: {dpy_version}\n'
                f'Pip version: {pipver}\n'
                f'System arch: {platform.machine()}\n'
                f'User: {user_who_ran}\n'
                f'OS version: {osver}\n'
                f'Storage type: {driver}\n'
            )
            await ctx.send(content=fmt.block(discord.utils.escape_markdown(_info)))

    @commands.cooldown(1, 60, commands.BucketType.user)
    @commands.command(name='contact')
    async def _contact(self, ctx: Context, *, message: str):
        """Sends a message to Patbot's owner.

        This message will contain ONLY the following information:
            1. Your username and your account's UUID.
                The UUID is a unique numeric ID given by Discord.
                This ID is shown PUBLICLY to everyone that is in
                a server that you are in, and is not meant to be
                kept a secret.
            2. The server you contacted the owner from, if any.
                The name and UUID of the server will be sent.

        Once the message is sent, the owner will be able to reply
        to you through Patbot.
        """
        guild = ctx.guild
        author = ctx.author
        footer = f'User ID: {author.id}'

        if ctx.guild is None:
            source = 'through DM'
        else:
            source = f'from {guild.name}'
            footer += f'  |  Server ID: {guild.id}'

        description = f'Sent by {author.name} {source}'
        destination = self.bot.get_user(int(await self.config.creator_id()))
        if not destination:
            return await ctx.send(fmt.error, "An error occurred while finding the owner's DM!")

        embed = await ctx.default_embed(description=message)
        if author.avatar_url:
            embed.set_author(name=description, icon_url=author.avatar_url)
        else:
            embed.set_author(name=description)
        embed.set_footer(text=footer)

        try:
            await destination.send(embed=embed)
        except discord.Forbidden or discord.HTTPException:
            await ctx.send(fmt.error, "I couldn't send your message. The error has been logged and "
                                      "your message has been internally recorded. Sorry!")
        else:
            await ctx.react_or_send(fmt.success, 'Your message has been sent.')

    @perms.creator()
    @commands.command(name='dm')
    async def dm(self, ctx: Context, user_id: int, *, message: str):
        """Sends a DM to a user.
        This command needs a user ID to work.
        """
        destination = ctx.bot.get_user(user_id)
        if destination is None or destination.bot:
            return await ctx.send(fmt.error,
                                  'Invalid ID, user not found, or user is a bot. '
                                  'You can only send messages to people I share '
                                  'a server with.')
        prefix = (await self.config.prefixes())[0]
        description = "Patbot's Owner"
        content = f"You can reply to this message with `{prefix}contact`."
        embed = await ctx.default_embed(color=discord.Color.red(), description=message)
        embed.set_footer(text=content)
        if ctx.bot.user.avatar_url:
            embed.set_author(name=description, icon_url=ctx.bot.user.avatar_url)
        else:
            embed.set_author(name=description)

        try:
            await destination.send(embed=embed)
        except discord.HTTPException:
            await ctx.send(fmt.error, f"Sorry, I couldn't deliver your message to {description}.")
        else:
            await ctx.react_or_send(fmt.success, f'Message delivered to {destination}')


def setup(bot):
    bot.add_cog(Core(bot))
