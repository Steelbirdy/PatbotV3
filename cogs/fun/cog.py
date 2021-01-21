import aiohttp
import datetime
import discord
from discord.ext import commands
from googleapiclient.discovery import build
from io import BytesIO
import random as rand
from typing import Optional, Union

from core import Config, Context, Patbot, utils, permissions as perms
from core.formatting import success, warning, error, fatal, info, format_time
from core.menus import Confirm
from .resources.pokedex import pokedex


class Fun(commands.Cog):
    """A cog that has a bunch of fun miscellaneous commands."""

    def __init__(self, bot: Patbot):
        self.bot = bot
        self.config = Config.get_config(cog_instance=self)
        self._register_defaults()
        self._quotes_history = None
        self._images = {}
        self._search = None

        if not hasattr(bot, '_current_petition'):
            self.bot._current_petition = None
            self._current_listener = None
        elif self.bot._current_petition is not None:
            self._current_listener = self._get_vote_listener(self.bot._current_petition['channel'])
            self.bot.add_listener(self._current_listener, 'on_message')
        else:
            self._current_listener = None

        self.bot.loop.create_task(self._init_petition())

    def _register_defaults(self):
        self.config.register_guild(
            counters=dict()
        )

    async def _init_petition(self):
        if self.bot._current_petition is not None and self._current_listener is None:
            try:
                start_time: int = self.bot._current_petition['start']
                start_time: datetime.datetime = datetime.datetime.fromordinal(start_time)
                await self.bot.wait_for('on_petition_end',
                                        timeout=float((60*60*24) - (datetime.datetime.now() - start_time).seconds))
            finally:
                message = self.bot.get_channel(self.bot._current_petition['channel'])
                message = await message.fetch_message(self.bot._current_petition['message'])
                ctx = await self.bot.get_context(message)
                await self._end_petition(ctx)

    async def get_image(self, ctx: Context, name: str) -> Optional[discord.File]:
        if name in self._images:
            return await self._images[name].to_file()
        async for message in ctx.guild.get_channel(625764441862045718).history(limit=None):
            if message.attachments:
                for attc in message.attachments:
                    _name = attc.url.split('/')[-1].split('.')[0]
                    if name == _name:
                        self._images[name] = attc
                        return await self._images[name].to_file()

    async def get_quotes(self, ctx: Context):
        if self._quotes_history is None:
            self._quotes_history = await ctx.guild.get_channel(390905817907331073).history(limit=None).flatten()
            self._quotes_history = list(filter(lambda m: any(x in m for x in {'"', '“', '-', '20'}),
                                               map(lambda x: x.content, self._quotes_history)))
        return self._quotes_history

    async def filter_quotes(self, ctx: Context, query: str = None):
        if query is None:
            return await self.get_quotes(ctx)
        query = query.lower()
        quotes = await self.get_quotes(ctx)
        if len(query) == 1:
            return list(filter(lambda msg:
                               msg.content.lower().endswith(query) or
                               any(x + query + ' ' in msg.content.lower() for x in {' ', '-'}), quotes))
        else:
            return list(filter(lambda msg: any(x + query in msg.content.lower() for x in {' ', '~', '-'}), quotes))

    @perms.meme_team()
    @commands.command(name='randomquote', aliases=['rq'])
    async def _randomquote(self, ctx: Context, *, query: str = None):
        """Retrieves a random quote that contains the query.
        """
        async with ctx.typing():
            quotes = await self.filter_quotes(ctx, query)
            if len(quotes) == 1:
                selected = quotes[0]
            else:
                selected = quotes[rand.randint(0, len(quotes) - 1)]
            await ctx.send(content='>>> ' + selected)
        await ctx.react(success)

    @perms.meme_team()
    @commands.command(name='listquote', aliases=['lq'])
    async def _listquotes(self, ctx: Context, *, query: str = None):
        """Retrieves a list of 10 random quotes that contain the query.
        """
        async with ctx.typing():
            quotes = await self.filter_quotes(ctx, query)
            rand.shuffle(quotes)
            selected = quotes[:min(len(quotes), 10)]
            await ctx.send(content=">>> " + '\n'.join(selected))
        await ctx.react(success)

    @commands.command(name='brunch')
    async def _brunch(self, ctx: Context):
        """Sends a picture of a sunnyside-up egg
        """
        url = 'https://cdn.apartmenttherapy.info/image/fetch/f_jpg,q_auto:eco,c_fill,g_auto,w_1500,' \
              'ar_1:1/https%3A%2F%2Fstorage.googleapis.com%2Fgen-atmedia%2F3%2F2019%2F03' \
              '%2F92b6a3e5ca345f34645cf203987ac9a04dd6727e.jpeg '
        await ctx.send(file=discord.File(await utils.get_image(ctx, url), filename='brunch.jpg'))

    @commands.command(name='meat')
    async def _meat(self, ctx: Context):
        """Yum yum!
        """
        await ctx.send(content='Yum yum!')

    @perms.meme_team()
    @commands.command(name='fail')
    async def _fail(self, ctx: Context):
        """Don Cheadle amirite"""
        try:
            await ctx.send(file=await self.get_image(ctx, 'fail'))
        finally:
            await ctx.safe_delete()

    @perms.meme_team()
    @commands.command(name='gazoo')
    async def _gazoo(self, ctx: Context):
        """DEMATERIALIZE!"""
        try:
            await ctx.send(content='***OOOOUWWUH***', file=await self.get_image(ctx, 'gazoo'))
        finally:
            pass

    @commands.command(name='pokefusion', aliases=['pf'])
    async def _pokefusion(self, ctx: Context, *, pokemon: str):
        """Pokefusion! Only works with the first 151 Pokemon.
        Separate the names of the two Pokemon with a comma.
        """
        names = [x.strip().lower() for x in pokemon.split(',')]
        if len(names) != 2:
            await ctx.react(error)
            return await ctx.send_help()
        numbers = [pokedex.get(x, None) for x in names]
        if numbers[0] is None:
            return await ctx.send(error, f'{names[0].title()} is not a valid Gen 1 Pokemon.')
        if numbers[1] is None:
            return await ctx.send(error, f'{names[1].title()} is not a valid Gen 1 Pokemon.')
        url = 'https://images.alexonsager.net/pokemon/fused/{0}/{0}.{1}.png'.format(*numbers)
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    buffer = BytesIO(await resp.read())
                else:
                    pass
        await ctx.send(file=discord.File(buffer, filename='pokefusion_{0}_{1}.png'.format(*numbers)))
        await ctx.react(success)

    @commands.command(name='everypony')
    @commands.cooldown(1, 86400)
    async def _everypony(self, ctx: Context):
        """Only Joey needs to know what this does."""
        if ctx.author.id != 173950689947418624:
            return
        ep_role = discord.utils.find(lambda x: x.name.lower() == 'everypony', ctx.guild.roles)
        content = f"What's up {ep_role.mention} UwU\n" \
                  f"|| *This message paid for by Josiah Vieland* ||"
        await ctx.send(content=content)

    @commands.command(name='milkshame', aliases=['ms', 'agedham'])
    async def _milkshame(self, ctx: Context, *, target: Union[discord.Member, str]):
        """If you don't know what it does, you don't belong"""
        shame = rand.choice(["{target} is a filthy milk-drinker",
                             "I hope {target} cries over spilled milk",
                             "{target}, you know what we do to milk-drinkers, right?",
                             "{target} is a big milk baby",
                             "{target}, you milky wilky baby",
                             "Pfft, {target}, what an absolute milk-drinker",
                             "{target} you milky bitch"])
        if isinstance(target, discord.Member) and target == ctx.me:
            return await ctx.send(content=shame.format(target=ctx.author.mention))
        if isinstance(target, discord.Member):
            target = target.mention
        await ctx.send(content=shame.format(target=target), file=await self.get_image(ctx, 'milkshame'))
        await ctx.react(success)

    @commands.command(name='scag')
    async def _scag(self, ctx: Context):
        """Joey is a scag."""
        joey = ctx.guild.get_member(173950689947418624)
        if joey not in ctx.channel.members:
            return await ctx.send(error, 'Joey is not in this channel.')
        await ctx.send(content=f'{joey.mention} you scag')

    @commands.command(name='thanks')
    async def _thanks(self, ctx: Context):
        """You're welcome!"""
        await ctx.send(content='🥰')

    async def _get_petition_embed(self, ctx: Context) -> discord.Embed:
        p = self.bot._current_petition
        emb = await ctx.default_embed(title=p['name'])
        emb.set_author(name='Started by ' + ctx.guild.get_member(p['author']).display_name, icon_url=ctx.guild.icon_url)
        emb.set_footer(text=f'Send `yay`, `nay`, or `meh` in #{ctx.channel.name} to vote.')
        votes = p['votes']
        emb.add_field(name='Yays', value=str(votes[0]), inline=True)
        emb.add_field(name='Nays', value=str(votes[1]), inline=True)
        emb.add_field(name='Mehs', value=str(votes[2]), inline=True)
        emb.add_field(name='Votes Needed', value=str(9 - sum(votes)), inline=False)
        return emb

    def _get_vote_listener(self, channel: int):
        async def vote_listener(message: discord.Message):
            ctx = await self.bot.get_context(message)
            if ctx.channel.id != channel:
                return
            content = message.content.lower()
            if content not in ('yea', 'yay', 'nay', 'meh'):
                return
            current = self.bot._current_petition
            if message.author.id in current['voters']:
                return
            current['voters'].append(message.author.id)
            votes = current['votes']
            if content in ('yea', 'yay'):
                votes[0] += 1
            elif content == 'nay':
                votes[1] += 1
            else:
                votes[-1] += 1
            if sum(votes) < 9 and votes[1] < 4:
                message = await ctx.channel.fetch_message(current['message'])
                await message.edit(embed=await self._get_petition_embed(ctx))
            else:
                self.bot.dispatch('on_petition_end')
        return vote_listener

    @perms.meme_team()
    @commands.group(name='petition', invoke_without_command=True)
    async def _petition(self, ctx: Context, *, name: str = None):
        """Starts a petition in the #congress channel."""
        _emoji = ':scales:'
        name = discord.utils.escape_mentions(name)

        if ctx.channel.id not in (384516853386706964, 654496310275342366):
            return await ctx.send(error,
                                  f'Petitions can only be created in '
                                  f'{ctx.guild.get_channel(384516853386706964).mention}.')
        if name is None:
            if not self.bot._current_petition:
                return await ctx.send(_emoji, "There isn't currently a petition running.")
            return await ctx.send(content='Note that this message will not update. Check the pinned messages.',
                                  embed=await self._get_petition_embed(ctx))
        if self.bot._current_petition:
            await ctx.send(_emoji, 'There is already a petition currently running.')
            await ctx.invoke(self._petition, name=None)
            return
        message = await ctx.send(_emoji, 'Loading...')
        self.bot._current_petition = {
            'message': message.id,
            'name': name,
            'author': ctx.author.id,
            'votes': [0, 0, 0],
            'channel': ctx.channel.id,
            'start': datetime.datetime.now().toordinal(),
            'voters': []
        }
        await message.edit(content=None, embed=await self._get_petition_embed(ctx))
        await message.pin()
        await ctx.react(success)
        listener = self._get_vote_listener(ctx.channel.id)
        self._current_listener = listener
        self.bot.add_listener(listener, 'on_message')
        try:
            await self.bot.wait_for('on_petition_end', timeout=float(60 * 60 * 24))
        finally:
            await ctx.invoke(self._petition_stop)

    @perms.meme_team()
    @_petition.command(name='stop')
    async def _petition_stop(self, ctx: Context):
        _emoji = ':scales:'
        if self.bot._current_petition is None:
            return await ctx.send(_emoji, "There isn't currently a petition running.")
        if not ctx.bot.is_owner(ctx.author) and not ctx.author.id == self.bot._current_petition['author']:
            return await ctx.send(error, "You can't end this petition.")
        await self._end_petition(ctx)
        await ctx.react(success)

    async def _end_petition(self, ctx: Context):
        _emoji = ':scales:'
        self.bot.remove_listener(self._current_listener, name='on_message')
        self._current_listener = None
        current = self.bot._current_petition
        votes = current['votes']
        message = self.bot.get_channel(self.bot._current_petition['channel'])
        message = await message.fetch_message(self.bot._current_petition['message'])
        if sum(votes) < 9 or votes[1] > 4:
            await ctx.send(_emoji, f'The petition **{current["name"]}** failed!')
            await message.unpin()
        else:
            await ctx.send(_emoji, f'The petition **{current["name"]}** passed!')
        emb = await self._get_petition_embed(ctx)
        emb.title = '[Closed] ' + emb.title
        await message.edit(embed=emb)
        self.bot._current_petition = None

    @commands.command(name='meme')
    async def _meme(self, ctx: Context, *, query: str):
        """Searches Google for memes."""
        async with self.config.customsearch() as credentials:
            if self._search is None:
                self._search = build('customsearch', 'v1', developerKey=credentials['key'])
            query += ' meme'
            results = self._search.cse().list(
                q=query,
                fileType="png, jpg",
                searchType="image",
                alt="json",
                cx=credentials['cx']
            ).execute()['items']
        if len(results) == 0:
            return await ctx.send(error, 'No results.')
        rand.shuffle(results)
        for item in results:
            if 'imgflip' not in item['link'] and item['link'].endswith(('.jpg', '.png')):
                break
        url = item['link']
        extension = url[url.rindex('.') + 1:].lower()
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as response:
                    r = await response.read()
            except aiohttp.ClientError:
                return await ctx.send(error, 'An invalid image was retrieved, please try again.')
            else:
                with BytesIO(r) as image:
                    await ctx.send(file=discord.File(image, filename=query + '.' + extension))
                    await ctx.react(success)

    @perms.meme_team()
    @commands.cooldown(1, 43200, commands.BucketType.user)
    @commands.command(name='bonk')
    async def _bonk(self, ctx: Context, user: discord.Member = ...):
        """BONK"""
        if user is ...:
            await ctx.send(info, 'A bonk is ready to deploy on your command.')
            raise commands.DisabledCommand
        if user.voice.channel is None:
            raise commands.UserInputError
        await ctx.send(success, '__***BONK***__')
        await ctx.react(success)
        await user.move_to(ctx.guild.get_channel(643286466566291496))

    @_bonk.error
    async def _bonk_error(self, ctx: Context, err):
        if type(err) == commands.CommandOnCooldown:
            return await ctx.send(content=f'Your bonk will be ready in '
                                          f'`{format_time(int(err.retry_after))}`.')
        elif type(err) == commands.UserInputError:
            await ctx.send(error, f'That user is not in a voice channel.')
        self._bonk.reset_cooldown(ctx)

    @commands.cooldown(1, 60*60*24*7, commands.BucketType.user)
    @commands.command(name='SCATTER')
    async def _scatter(self, ctx: Context):
        """SCATTER!!!"""
        await ctx.send(success, '__***SCATTER!!!***__')
        await ctx.react(success)
        vcs = ctx.guild.voice_channels
        members = {vc: vc.members for vc in vcs}
        indices = set(range(0, len(vcs)))
        for i, vc in enumerate(vcs):
            for member in members[vc]:
                r = rand.choice(list(indices - {i}))
                await member.move_to(vcs[r])

    @_scatter.error
    async def _scatter_error(self, ctx: Context, err):
        if type(err) == commands.CommandOnCooldown:
            return await ctx.send(content=f'Your scatter will be ready in '
                                          f'`{format_time(int(err.retry_after))}`.')
        self._scatter.reset_cooldown(ctx)

    @staticmethod
    async def _display_counter(ctx: Context, name: str, value: int):
        content = f'**{name}**  :  `{value}`'
        if await ctx.accepts_embeds():
            embed = await ctx.default_embed(title=content)
            await ctx.send(embed=embed)
        else:
            await ctx.send(info, content)

    @commands.group('counter', aliases=['counters'], invoke_without_command=True)
    async def _counter(self, ctx: Context, name: str, op: str = None, value: int = None):
        """Custom counters to track stuff.

        * Doing <Name> + <Num> increases <Name>'s value by <Num>. If <Num> is not given, 1 is the default value.
        * Doing <Name> - <Num> decreases <Name>'s value by <Num>. If <Num> is not given, 1 is the default value.
        * Doing <Name> = <Num> sets <Name>'s value to <Num>
        """
        async with self.config.guild(ctx).counters() as counters:
            if name not in counters:
                return await ctx.send(error, f'No counter named `{name}` exists.')
            if op is None and value is None:
                return await self._display_counter(ctx, name, counters[name])
            if value is None:
                if op in {'+', '-'}:
                    value = 1
                else:
                    return await ctx.send_help(ctx.command)
            if op == '+':
                counters[name] += value
            elif op == '-':
                counters[name] -= value
            elif op == '=':
                counters[name] = value
            else:
                return await ctx.send_help(ctx.command)
            return await self._display_counter(ctx, name, counters[name])

    @_counter.command('list')
    async def _counter_list(self, ctx: Context):
        """Lists the server's counters.
        """
        async with self.config.guild(ctx.guild).counters() as counters:
            if not counters:
                return await ctx.send(info, 'No counters have been created on this server.')
            content = '\n'.join(f'**{name}**  :  `{value}`' for name, value in counters.items())
        if await ctx.accepts_embeds():
            embed = await ctx.default_embed(title=f'**Counters**', description=content)
            await ctx.send(embed=embed)
        else:
            content = f'**Counters**\n------------\n' + content
            await ctx.send(content=content)

    @_counter.command('create')
    async def _counter_create(self, ctx: Context, name: str, value: int = 0):
        """Creates a new counter.
        You can optionally give a starting value, which defaults to 0.
        """
        async with self.config.guild(ctx).counters() as counters:
            if name in counters:
                return await ctx.send(error, f'A counter named `{name}` already exists.')
            counters[name] = value
        await self._display_counter(ctx, name, value)

    @_counter.command('rename')
    async def _counter_rename(self, ctx: Context, old_name: str, new_name: str):
        """Renames a counter."""
        async with self.config.guild(ctx).counters() as counters:
            if old_name not in counters:
                return await ctx.send_help(ctx.command)
            if new_name in counters:
                return await ctx.send_help(ctx.command)
            counters[new_name] = counters[old_name]
            del counters[old_name]
            await self._display_counter(ctx, new_name, counters[new_name])

    @_counter.command('delete', aliases=['remove'])
    async def _counter_delete(self, ctx: Context, name: str):
        """Deletes a counter."""
        async with self.config.guild(ctx).counters() as counters:
            if name not in counters:
                return await ctx.send(error, f'No counter named `{name}` exists.')
            result = await Confirm(f'Are you sure you want to delete the counter `{name}`?').prompt(ctx)
            if result:
                del counters[name]
                await ctx.react_or_send(success, f'The counter `{name}` was deleted.')


def setup(bot):
    bot.add_cog(Fun(bot))
