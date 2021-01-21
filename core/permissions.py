import discord
from discord.ext import commands
from discord.ext.commands import Context
import enum
from typing import Awaitable, Callable, Optional, Union
from core.config import Config


CheckPredicate = Callable[[Context], Union[Optional[bool], Awaitable[Optional[bool]]]]
settings_config = Config.get_config(cog_name='settings')

DM_PERMISSIONS = discord.Permissions(
    add_reactions=True,
    attach_files=True,
    embed_links=True,
    external_emojis=True,
    mention_everyone=True,
    read_message_history=True,
    read_messages=True,
    send_messages=True,
)


class PermissionsLevel(enum.IntEnum):
    NONE = 0
    MOD = 1
    ADMIN = 2
    GUILD_OWNER = 3
    BOT_OWNER = 4
    BOT_CREATOR = 5

    @classmethod
    async def from_ctx(cls, ctx: Context) -> "PermissionsLevel":
        if ctx.author.id == await ctx.bot.config.creator_id():
            return cls.BOT_CREATOR
        if await ctx.bot.is_owner(ctx.author):
            return cls.BOT_OWNER
        if ctx.guild is None:
            return cls.NONE
        if ctx.author == ctx.guild.owner:
            return cls.GUILD_OWNER

        guild_settings = settings_config.guild(ctx)
        roles = set(ctx.author.roles)

        if 'admin' in roles or 'administrator' in roles or \
                any(role in roles for role in await guild_settings.admin_roles()):
            return cls.ADMIN
        if 'mod' in roles or 'moderator' in roles or \
                any(role in roles for role in await guild_settings.mod_roles()):
            return cls.MOD
        return cls.NONE

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}.{self.name}>'


def user_has_permissions(ctx: Context, *, user: discord.abc.User = None, **perms) -> bool:
    if user is None:
        user = ctx.author
    if ctx.guild:
        return ctx.channel.permissions_for(user) >= discord.Permissions(**perms)
    else:
        return DM_PERMISSIONS >= discord.Permissions(**perms)


def author_has_permissions(ctx: Context, **perms) -> bool:
    if ctx.guild:
        return ctx.channel.permissions_for(ctx.author) >= discord.Permissions(**perms)
    else:
        return DM_PERMISSIONS >= discord.Permissions(**perms)


def user_has_any_role(user: discord.Member, *roles: str) -> bool:
    if not isinstance(user, discord.Member):
        return False
    names = map(lambda x: x.name.lower(), user.roles)
    return any(r.lower() in names for r in roles)


def author_has_any_role(ctx: Context, *roles: str) -> bool:
    if not ctx.guild:
        return False
    return user_has_any_role(ctx.author, *roles)


def user_has_all_roles(user: discord.Member, *roles: str) -> bool:
    if not isinstance(user, discord.Member):
        return False
    names = map(lambda x: x.name.lower(), user.roles)
    return all(r.lower() in names for r in roles)


def author_has_all_roles(ctx: Context, *roles: str) -> bool:
    if not ctx.guild:
        return False
    return user_has_all_roles(ctx.author, *roles)


def meme_team() -> CheckPredicate:
    def predicate(ctx: Context) -> bool:
        return ctx.guild.id == 300755943912636417
    return commands.check(predicate)


def creator() -> CheckPredicate:
    async def predicate(ctx: Context) -> bool:
        return ctx.author.id == int(await ctx.bot.config.creator_id())
    return commands.check(predicate)


def owner() -> CheckPredicate:
    def predicate(ctx: Context) -> bool:
        return ctx.bot.is_owner(ctx.author)
    return commands.check(predicate)


def guildowner() -> CheckPredicate:
    async def predicate(ctx: Context) -> bool:
        return ctx.guild and await PermissionsLevel.from_ctx(ctx) >= PermissionsLevel.GUILD_OWNER
    return commands.check(predicate)


def guildowner_or_permissions(**perms) -> CheckPredicate:
    async def predicate(ctx: Context) -> bool:
        return ctx.guild and (await PermissionsLevel.from_ctx(ctx) >= PermissionsLevel.GUILD_OWNER
                              or author_has_permissions(ctx, **perms))
    return commands.check(predicate)


def admin() -> CheckPredicate:
    async def predicate(ctx: Context) -> bool:
        return await PermissionsLevel.from_ctx(ctx) >= PermissionsLevel.ADMIN
    return commands.check(predicate)


def admin_or_permissions(**perms) -> CheckPredicate:
    async def predicate(ctx: Context) -> bool:
        return await PermissionsLevel.from_ctx(ctx) >= PermissionsLevel.ADMIN or \
            author_has_permissions(ctx, **perms)
    return commands.check(predicate)


def mod() -> CheckPredicate:
    async def predicate(ctx: Context) -> bool:
        return await PermissionsLevel.from_ctx(ctx) >= PermissionsLevel.MOD
    return commands.check(predicate)


def mod_or_permissions(**perms) -> CheckPredicate:
    async def predicate(ctx: Context) -> bool:
        return await PermissionsLevel.from_ctx(ctx) >= PermissionsLevel.MOD or \
            author_has_permissions(ctx, **perms)
    return commands.check(predicate)


def missing_permissions(required: discord.Permissions, actual: discord.Permissions):
    return discord.Permissions(required.value & ~actual.value)
