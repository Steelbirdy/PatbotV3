from collections import OrderedDict
import discord
from discord.ext import commands
from discord.ext.commands import Greedy
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

from cogs.polling.core.polling import SimpleDynamicPoll, AnonymousDynamicPoll, SimpleStaticPoll

from core import Config, Context, Patbot, CommandArgument
from core.formatting import success, warning, error, fatal, info
from core import permissions as perms


class Polling(commands.Cog):
    """A template cog to use as a starting point for creating new ones. Doesn't have any commands of its own."""
    def __init__(self, bot: Patbot):
        self.bot = bot
        self.config = Config.get_config(cog_instance=self)
        self._register_defaults()

    def _register_defaults(self):
        self.config.register_guild(
            enabled=True,
            commands={
                'polltest': True
            }
        )

    @staticmethod
    def _parse_args(cmd: str) -> Dict[str, Any]:
        """Format: !!poll [-h/-hidden] [-anon/-anonymous] <Title>, <Option 1>, <Option 2>[, ...]"""
        options = re.split(r'\s*,\s*', cmd)
        argstitle, options = options[0], options[1:]
        args = []
        title = ''
        for word in argstitle.split():
            if word.startswith('-'):
                args.append(word[1:])
            else:
                title += word + ' '
        return {
            'title': title.strip(),
            'args': args,
            'options': options
        }

    @staticmethod
    def _map_emojis(options: Sequence[str]) -> OrderedDict:
        if len(options) < 10:  # Use numbers
            em = ['{}\N{COMBINING ENCLOSING KEYCAP}'.format(str(x)) for x in range(1, 10)]
        else:
            raise ValueError('Must be at most 9 options')
        return OrderedDict(**{em[i - 1]: option for i, option in enumerate(options, start=1)})

    @staticmethod
    def _convert_bool_arg(arg) -> Optional[bool]:
        if isinstance(arg, bool):
            return arg
        lowered = str(arg).lower()
        if lowered in ('yes', 'y', 'true', 't', '1', 'enable', 'on'):
            return True
        elif lowered in ('no', 'n', 'false', 'f', '0', 'disable', 'off', 'none'):
            return False
        else:
            return None

    @classmethod
    def _convert_poll_args(cls, ctx: Context, args: List[Tuple[str, Optional[str]]]):
        valid_args = {
            ('anon', 'a', 'anonymous'): cls._convert_bool_arg
        }
        found_args = {}
        args = dict(args)
        for keys, converter in valid_args.items():
            for option in keys:
                if option in args:
                    if isinstance(converter, commands.Converter):
                        found_args[keys[0]] = converter.convert(ctx, args[option])
                    elif callable(converter):
                        found_args[keys[0]] = converter(args[option])
                    else:
                        raise commands.ConversionError(None, None)
                    break
        return found_args

    @commands.guild_only()
    @commands.command(name='poll')
    async def _poll(self, ctx: Context, args: Greedy[CommandArgument], title: str, *options: str):
        """Start a poll.
        You can optionally make the poll anonymous by putting "-anon" before the title (ex. !!poll -anon Title etc.)
        An example:

            !!poll "Which Jolly Rancher?" Green Blue Purple "None of them"

        Starts a (not anonymous) poll with the title "Which Jolly Rancher" and four options: "Green", "Blue", "Purple", and "None of them".
        If the title or an option is more than one word, you need to put the "" around it so that Patbot can parse it correctly.
        """
        args = args or []
        args = self._convert_poll_args(ctx, args)
        if args.get('anon', False) is True:
            poll_class = AnonymousDynamicPoll
        else:
            poll_class = SimpleDynamicPoll
        options = self._map_emojis(options)
        poll = poll_class(title, options)
        return await poll.start(ctx)


def setup(bot):
    bot.add_cog(Polling(bot))
