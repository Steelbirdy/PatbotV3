import discord
from discord.ext import commands, menus
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
        )

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
        if ctx.guild and ctx.guild.id == 765314921151332464:
            return await ctx.send(content=f'Here you go **{ctx.author.display_name}** :tada:\n'
                                          f'https://discord.gg/r6KXeYy')

    @commands.command(name='about', aliases=['info'])
    async def _about(self, ctx: Context):  # TODO: Wrap in info()
        """About Patbot."""
        properties = {
            'Version': self.bot.__version__,
            'Last boot': self.bot.last_boot.strftime("%B %d, %Y @ %I:%M%p"),
            'Developer': 'Steelbirdy#3536',
            'Library': 'discord.py'
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


def setup(bot):
    bot.add_cog(Core(bot))
