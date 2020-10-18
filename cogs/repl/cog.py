import asyncio
from contextlib import redirect_stdout
import discord
from discord.ext import commands
from io import StringIO
import inspect
import textwrap
import traceback
from typing import Awaitable, Callable, Union

from core import Config, Context, Patbot
from core.formatting import error, fatal, block
from core import permissions as perms


def _check_ctx(ctx: Context, *,
               predicate: Callable[[discord.Message], bool] = None
               ) -> Callable[[discord.Message], bool]:
    def inner(msg: discord.Message) -> bool:
        if predicate is not None and predicate(msg) is not True:
            return False
        return msg.channel == ctx.channel and msg.author == ctx.author
    return inner


def _cleanup_code(content: str):
    """Automatically removes code blocks from text."""
    # remove ```py\n```
    if content.startswith('```') and content.endswith('```'):
        return '\n'.join(content.split('\n')[1:-1])
    # remove `foo`
    return content.strip('` \n')


def _get_syntax_error(e):
    if e.text is None:
        return block(f'{type(e).__name__}: {e}')
    return block('{0.text}{1:>{0.offset}}\n{2}: {0}'.format(e, '^', type(e).__name__))


class Repl(commands.Cog, name='REPL'):
    """Allows Patbot to act as a Python REPL (Read-Eval-Print-Loop) interface for arbitrary code execution."""
    def __init__(self, bot: Patbot):
        self.bot = bot
        self.config = Config.get_config(cog_instance=self)
        self._register_defaults()
        self._last_result = None
        self._sessions = set()

    def _register_defaults(self):
        self.config.register_guild(
            enabled=True
        )

    @perms.creator()
    @commands.command(name="eval", hidden=True)
    async def _eval(self, ctx: Context, *, code: str):
        """Evaluates a single line of Python code."""
        env = {
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'server': ctx.guild,
            'guild': ctx.guild,
            'message': ctx.message,
            'ans': self._last_result,
            'Config': self.bot.config.__class__,
        }
        env.update(globals())

        code = _cleanup_code(code)
        stdout = StringIO()
        to_compile = 'async def func():\n{0}'.format(textwrap.indent(code, '\t'))

        try:
            exec(to_compile, env)
        except SyntaxError as e:
            return await ctx.send(fatal, _get_syntax_error(e))

        func = env['func']
        try:
            with redirect_stdout(stdout):
                tr = await func()
        except Exception as e:
            value = stdout.getvalue()
            await ctx.send(fatal, '\n' + block(f'{value}\n{traceback.format_exc()}'))
        else:
            value = stdout.getvalue()
            if tr is None:
                if value:
                    await ctx.send(':space_invader:', '**Output**' + block(value))
                else:
                    await ctx.send(':space_invader:', 'The `eval` ran successfully.')
            else:
                self._last_result = tr
                await ctx.send(':space_invader:', '**Output**' + block(value + '\n' + str(tr)))

    @perms.creator()
    @commands.command(name='repl', hidden=True)
    async def repl(self, ctx: Context):
        """Opens a REPL in the channel this is used."""
        env = {
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'server': ctx.guild,
            'guild': ctx.guild,
            'message': ctx.message,
            'ans': self._last_result,
            'Config': self.bot.config.__class__,
        }

        if ctx.channel.id in self._sessions:
            return await ctx.send(':space_invader:',
                                  'A REPL session is already running in this channel. '
                                  'Use `exit()` or `quit()` to exit.')
        self._sessions.add(ctx.channel.id)
        await ctx.send(':space_invader:', 'Enter code to execute or evaluate. Use `exit()` or `quit()` to exit.')
        while True:
            response = await self.bot.wait_for('message',
                                               check=_check_ctx(ctx, predicate=lambda m: m.content.startswith('`')),
                                               timeout=10.0 * 60)
            cleaned = _cleanup_code(response.content)
            if cleaned in ('quit', 'quit()', 'exit', 'exit()'):
                await ctx.send(':space_invader:', 'Exiting...')
                self._sessions.remove(ctx.channel.id)
                return

            executor = exec
            if cleaned.count('\n') == 0:
                # single statement, potentially 'eval'
                try:
                    code = compile(cleaned, '<repl session>', 'eval')
                except SyntaxError:
                    pass
                else:
                    executor = eval

            if executor is exec:
                try:
                    code = compile(cleaned, '<repl session>', 'exec')
                except SyntaxError as e:
                    await ctx.send(':space_invader:', _get_syntax_error(e))
                    continue

            env['message'] = response

            fmt = None
            stdout = StringIO()

            try:
                with redirect_stdout(stdout):
                    result = executor(code, env)
                    if inspect.isawaitable(result):
                        result = await result
            except Exception as e:
                value = stdout.getvalue()
                fmt = block(f'{value}\n{traceback.format_exc()}')
            else:
                value = stdout.getvalue()
                if result is not None:
                    fmt = block(f'{value}\n{result}')
                    env['ans'] = result
                elif value:
                    fmt = block(value)
            try:
                if fmt is not None:
                    if len(fmt) > 2000:
                        await ctx.send(':space_invader:', fmt[:1800] + '...')
                    else:
                        await ctx.send(':space_invader:', fmt)
            except discord.Forbidden:
                pass
            except discord.HTTPException as e:
                await ctx.send(fatal, f'Unexpected error: `{e}`')


def setup(bot):
    bot.add_cog(Repl(bot))
