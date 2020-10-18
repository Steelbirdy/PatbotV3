import discord

from core import Config, Context, formatting


_yn = lambda x: "Yes" if x else "No"


async def autoformat_cog(ctx: Context, config: Config, *, current_page: int = None, max_pages: int = None):
    if await ctx.accepts_embeds():
        return await cog_as_embed(ctx, config, current_page, max_pages)
    else:
        return await cog_as_string(ctx, config, current_page, max_pages)


async def cog_as_embed(ctx: Context, config: Config,
                       current_page: int = None, max_pages: int = None) -> discord.Embed:
    settings = config.cog_settings
    embed = await ctx.default_embed(title=await settings.cog_name())
    if current_page is not None:
        embed.set_footer(text=f'Cog {current_page}/{max_pages}')
    embed.description = await settings.description()

    cog_is_enabled = ctx.bot.get_cog(await settings.cog_name()) is not None
    if cog_is_enabled and ctx.guild and settings.allow_disable():
        cog_is_enabled = await config.guild(ctx).enabled() or cog_is_enabled

    fields = {
        'Version': '.'.join(str(x) for x in await settings.version()),
        'Hidden': _yn(await settings.hidden()),
        'Enabled': _yn(cog_is_enabled) if await settings.allow_disable() else "Always",
    }
    for k, v in fields.items():
        embed.add_field(name=k, value=v, inline=True)
    return embed


async def cog_as_string(ctx: Context, config: Config,
                        current_page: int = None, max_pages: int = None) -> str:
    settings = config.cog_settings

    cog_is_enabled = ctx.bot.get_cog(await settings.cog_name()) is not None
    if ctx.guild and settings.allow_disable():
        cog_is_enabled = await config.guild(ctx).enabled() or cog_is_enabled

    content = f'_{await settings.cog_name()}_\n' \
              f'**Version**:   {".".join(str(x) for x in await settings.version())}\n' \
              f'**Hidden** :   {_yn(await settings.hidden())}\n' \
              f'**Enabled**:   {_yn(cog_is_enabled) if await settings.allow_disable() else "Always"}'
    if current_page is not None:
        content += f'\n\nCog {current_page}/{max_pages}'
    return formatting.block(content, lang='md')
