import d20
import discord
from discord.ext import commands
import random
import string

from core import Config, Context, Patbot
from core.formatting import success, error
from core.menus import Confirm, SingleChoice
from .lib.genesys.lookup import *
from .lib.dnd import Cache
from .lib.dnd.display.spells import spell_info
from .lib.dnd.display.conditions import condition_info
from .lib.dnd.display.items import item_info, item_info2


class DnD(commands.Cog):
    """Allows dice rolling among other D&D utilities."""

    def __init__(self, bot: Patbot):
        self.bot = bot
        self.config = Config.get_config(cog_instance=self)
        self._register_defaults()
        self._d20 = '<:d20:734505366821404693>'
        self.banned_names = ('adv', 'a', 'dis', 'disadv', 'd', 'stats')
        self.cache = Cache()
        self._gathered = dict()

    def _register_defaults(self):
        self.config.register_global(macros={})
        self.config.register_guild(macros={})

    async def _replace_macros(self, ctx: Context, expr: str):
        async with self.config.macros() as macros:
            for name, value in macros.items():
                expr = expr.replace(name, '(' + value + ')')
        if ctx.guild is None:
            return expr
        async with self.config.guild(ctx.guild).macros() as macros:
            for name, value in macros.items():
                expr = expr.replace(name, '(' + value + ')')
        return expr

    @staticmethod
    async def format_and_send_genesys(ctx: Context, rolls: list):
        content = ', '.join(f'{roll} ({", ".join(result)})' for roll, result in rolls)
        results = {}
        for _, result in rolls:
            for c in ''.join(result):
                results[c] = results.get(c, 0) + 1
        final_results = {
            'SF': results.get('S', 0) - results.get('F', 0),
            'AT': results.get('A', 0) - results.get('T', 0),
            'TD': results.get('R', 0) - results.get('D', 0)
        }
        if final_results['SF'] >= 0:
            sf = str(final_results['SF']) + (' Success' if final_results['SF'] == 1 else ' Successes')
        else:
            sf = str(-final_results['SF']) + (' Failure' if final_results['SF'] == -1 else ' Failures')
        if final_results['AT'] >= 0:
            at = str(final_results['AT']) + (' Advantage' if final_results['AT'] == 1 else ' Advantages')
        else:
            at = str(-final_results['AT']) + (' Threat' if final_results['AT'] == -1 else ' Threats')
        if final_results['TD'] >= 0:
            td = str(final_results['TD']) + (' Triumph' if final_results['TD'] == 1 else ' Triumphs')
        else:
            td = str(-final_results['TD']) + (' Despair' if final_results['TD'] == -1 else ' Despairs')

        if await ctx.accepts_embeds():
            embed = await ctx.default_embed(title='Genesys Roll', color=await ctx.embed_color(), description=content)
            embed.description = content
            embed.add_field(name='Successes/Failures', value=sf)
            embed.add_field(name='Advantages/Threats', value=at)
            embed.add_field(name='Triumphs/Despairs', value=td)
            await ctx.send(embed=embed)
        else:
            content = '**Genesys Roll**\n' + content
            content += f'\n**Successes/Failures**: {sf}'
            content += f'\n**Advantages/Threats**: {at}'
            content += f'\n**Triumphs/Despairs**:  {td}'
            await ctx.send(content=content)

    @commands.group('roll', aliases=['r'], invoke_without_command=True)
    async def _roll(self, ctx: Context, *, expr: str = '1d20'):
        """Rolls dice!
        This library has very similar syntax: https://d20.readthedocs.io/en/latest/start.html#dice-syntax"""
        msg: discord.Message = await ctx.send(self._d20, 'Rolling...')
        expr = await self._replace_macros(ctx, expr)
        result: d20.RollResult = d20.roll(expr)
        await msg.edit(content=f'{self._d20} {str(result)}')

    @_roll.command('stats')
    async def _roll_stats(self, ctx: Context):
        """Rolls stats as used in D&D 5th Edition: 6 x 4d6kh3"""
        msg: discord.Message = await ctx.send(self._d20, 'Rolling...')
        results = [d20.roll('4d6kh3') for _ in range(6)]
        content = '\n'.join(f'{i + 1}: {results[i]}' for i in range(len(results)))
        if await ctx.accepts_embeds():
            embed = await ctx.default_embed(title='Stat Rolls', description=content, color=await ctx.embed_color())
            await msg.edit(content='', embed=embed)
        else:
            content = '**Stat Rolls**\n\n' + content
            await msg.edit(content=content)

    @_roll.command('advantage', aliases=['adv', 'a'])
    async def _roll_advantage(self, ctx: Context, *, expr: str = '1d20'):
        """Roll with advantage"""
        msg: discord.Message = await ctx.send(self._d20, 'Rolling...')
        expr = await self._replace_macros(ctx, expr)
        result: d20.RollResult = d20.roll(expr, advantage=d20.AdvType.ADV)
        await msg.edit(content=f'{self._d20} {str(result)}')

    @_roll.command('disadvantage', aliases=['disadv', 'dis', 'd'])
    async def _roll_disadvantage(self, ctx: Context, *, expr: str = '1d20'):
        """Roll with disadvantage"""
        msg: discord.Message = await ctx.send(self._d20, 'Rolling...')
        expr = await self._replace_macros(ctx, expr)
        result: d20.RollResult = d20.roll(expr, advantage=d20.AdvType.DIS)
        await msg.edit(content=f'{self._d20} {str(result)}')

    @commands.group('macro', aliases=['macros'], invoke_without_command=True)
    async def _macro(self, ctx: Context, name: str):
        """Manage server-wide macros for dice rolling."""
        _globals = await self.config.macros.all()
        if name in _globals:
            content = f'`{name}`  :  `{_globals[name]}`'
            if await ctx.accepts_embeds():
                embed = await ctx.default_embed(title=content, color=await ctx.embed_color())
                return await ctx.send(embed=embed)
            else:
                return await ctx.send(self._d20, content)
        async with self.config.guild(ctx.guild).macros() as macros:
            if name not in macros:
                return  # TODO: Help
            content = f'`{name}`  =  `{macros[name]}`'
            if await ctx.accepts_embeds():
                embed = await ctx.default_embed(title=content, color=await ctx.embed_color())
                return await ctx.send(embed=embed)
            else:
                return await ctx.send(self._d20, content)

    @_macro.group('create', invoke_without_subcommand=True)
    async def _macro_create(self, ctx: Context, name: str, *, value: str):
        """Create a new macro for dice rolling. The name must be a single word, and the value
        must be a valid [d20](https://github.com/avrae/d20) expression."""
        if name in self.banned_names:
            return await ctx.send(error, f'That name is not allowed.')
        if name in await self.config.macros.all():
            return await ctx.send(error, f'There is already a global macro named `{name}`.')
        async with self.config.guild(ctx.guild).macros() as macros:
            if name in macros:
                return await ctx.send(error, f'A macro named `{name}` already exists.')
            macros[name] = value
        await ctx.send(success, f'A macro named `{name}` for `{value}` has been created.')

    @_macro.command('set')
    async def _macro_set(self, ctx: Context, name: str, *, value: str):
        """Sets the value of a dice-rolling macro."""
        async with self.config.guild(ctx.guild).macros() as macros:
            if name not in macros:
                return await ctx.send(error, f'No macro named `{name}` exists.')
            macros[name] = value
        await ctx.send(success, f'The macro `{name}` now means `{value}`.')

    @_macro.command('rename')
    async def _macro_rename(self, ctx: Context, old_name: str, new_name: str):
        """Renames a dice-rolling macro."""
        if new_name in self.banned_names:
            return await ctx.send(error, f'That name is not allowed.')
        async with self.config.guild(ctx.guild).macros() as macros:
            if old_name not in macros:
                return await ctx.send(error, f'No macro named `{old_name}` exists.')
            if new_name in macros or new_name in await self.config.macros.all():
                return await ctx.send(error, f'A macro named `{new_name}` already exists.')
            macros[new_name] = macros[old_name]
            del macros[old_name]
        await ctx.send(success, f'The macro `{old_name}` has been renamed to `{new_name}`.')

    @_macro.command('list')
    async def _macro_list(self, ctx: Context):
        """Lists all macros available in the current scope."""
        _global_macros = await self.config.macros.all()
        async with self.config.guild(ctx.guild).macros() as macros:
            content = '**Global Macros**\n'
            content += '\n'.join(f'**{name}**  =  `{value}`' for name, value in _global_macros.items())
            content += '\n\n**Server Macros**\n'
            content += '\n'.join(f'**{name}**  =  `{value}`' for name, value in macros.items())
            if await ctx.accepts_embeds():
                embed = await ctx.default_embed(title='Dice Macros', description=content,
                                                color=await ctx.embed_color())
                await ctx.send(embed=embed)
            else:
                await ctx.send(content=content)

    @_macro.command('delete', aliases=['remove'])
    async def _macro_delete(self, ctx: Context, name: str):
        """Deletes a macro."""
        async with self.config.guild(ctx.guild).macros() as macros:
            if name not in macros:
                return await ctx.send(error, f'No macro named `{name}` exists.')
            result = Confirm(f'Are you sure you want to delete the macro `{name}`?').start(ctx, wait=True)
            if result:
                del macros[name]
                await ctx.send(success, f'The macro `{name}` was deleted.')

    @commands.command('genesys', aliases=['gen'])
    async def _genesys(self, ctx: Context, *dice: str):
        """Rolls Genesys dice.
        format: !!gen [Na] [Nb] [Nc] [Nd] [Np] [Ns]
        ex. !!gen 2d 2a 1p
        where each N is the number of dice of that type.

        * a: ability dice
        * b: boost dice
        * c: challenge dice
        * d: difficulty dice
        * p: proficiency dice
        * s: setback dice
        """
        lookup = {
            'a': ability,
            'b': boost,
            'c': challenge,
            'd': difficulty,
            'p': proficiency,
            's': setback
        }
        rolls = []
        for die in dice:
            if len(die) == 1:
                die = '1' + die
            results = []
            num = int(die[:-1])
            typ = die[-1]
            if typ not in lookup:
                return await ctx.send(error, f'{typ} is not a valid Genesys die type.')

            for _ in range(num):
                result = lookup[typ][random.randint(0, len(lookup[typ]) - 1)]
                results.append(result)

            rolls.append((die, results))
        await self.format_and_send_genesys(ctx, rolls)

    async def _send_cache_loading(self, ctx: Context):
        if self.cache.initialized:
            return None
        if await ctx.accepts_embeds():
            embed = await ctx.default_embed(title=self._d20 + ' Loading cache... this might take a few seconds...')
            message = await ctx.send(embed=embed)
        else:
            message = await ctx.send(self._d20, 'Loading cache... this might take a few seconds...')
        await self.cache.initialize(ignore_ua=True)
        return message

    async def _send_choice(self, ctx: Context, choices: list, content: str, message: discord.Message):
        menu = SingleChoice([string.capwords(string.capwords(c, '('), ' ') for c in choices], content,
                            delete_message_after=False, message=message)
        result = await menu.prompt(ctx)
        return result

    async def _get_user_choice(self, ctx: Context, type: str, query: str):
        message = await self._send_cache_loading(ctx)

        choices = getattr(self.cache, f'get_{type}_fuzzy')(query)
        if len(choices) != 1:
            result = await self._send_choice(ctx, choices, f'Which {type} do you mean?', message)
            if result is None:
                if await ctx.accepts_embeds():
                    embed = await ctx.default_embed(title='(Search cancelled)')
                    await message.edit(embed=embed)
                else:
                    await message.edit(content='**(Search cancelled)**')
                return None, None
        else:
            result = choices[0]
        return result, message

    @commands.command(name='spell', aliases=['spells'])
    async def _spell(self, ctx: Context, *, spell_name: str):
        """Displays a D&D spell's entry.
        PLEASE NOTE: This information is taken from a website's database on the interwebs and might be inaccurate.
        If those mistakes are caught I will fix it when the spell is displayed, but I can't fix the website's database.

        Also there are probably things I missed when programming how the spell displays, so let me know if you find any.
        """
        result, message = await self._get_user_choice(ctx, 'spell', spell_name)
        if result is None:
            return

        gathered = self._gathered.setdefault('spell', dict())
        spell = gathered.setdefault(result, spell_info(self.cache.get_spell(result)))
        if await ctx.accepts_embeds():
            return await spell.send_as_embed(ctx, message)
        else:
            return await spell.send_as_message(ctx, message)

    @commands.command(name='condition', aliases=['conditions', 'cond'])
    async def _condition(self, ctx: Context, *, condition_name: str):
        """Displays a D&D condition's entry."""
        result, message = await self._get_user_choice(ctx, 'condition', condition_name)
        if result is None:
            return

        gathered = self._gathered.setdefault('condition', dict())
        condition = gathered.setdefault(result, condition_info(self.cache.get_condition(result)))
        if await ctx.accepts_embeds():
            return await condition.send_as_embed(ctx, message)
        else:
            return await condition.send_as_message(ctx, message)

    @commands.command(name='item', aliases=['items'])
    async def _item(self, ctx: Context, *, item_name: str):
        """Displays a D&D item's entry."""
        result, message = await self._get_user_choice(ctx, 'item', item_name)
        if result is None:
            return

        gathered = self._gathered.setdefault('item', dict())
        item = gathered.setdefault(result, item_info2(self.cache.get_item(result)))
        if await ctx.accepts_embeds():
            # return await item.send_as_embed(ctx, message)
            return await item.send_as_embeds(ctx, message)
        else:
            # return await item.send_as_message(ctx, message)
            return await item.send_as_messages(ctx, message)


def setup(bot):
    bot.add_cog(DnD(bot))
