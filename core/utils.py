import aiohttp
from io import BytesIO

from core.context import Context


async def get_image(ctx: Context, url: str = None) -> BytesIO:
    """
    Tries to derive an image from the context.
    If the `url` parameter is filled, it uses that. Otherwise,
    if the message has an attachment, it uses that. Otherwise,
    it searches the last 10 messages sent in the channel for an image.
    :param ctx: The context to search in.
    :param url: If given, grabs the image from here.
    :return: The BytesIO object of the image.
    """
    async def from_attc():
        if ctx.message.attachments[0].filename.split('.')[-1].lower() in ('jpg', 'png'):
            ret = BytesIO()
            await ctx.message.attachments[0].save(ret, seek_begin=True)
            return ret

    if url is not None:
        try:
            async with aiohttp.ClientSession().get(url) as response:
                r = await response.read()
                return BytesIO(r)
        except aiohttp.ClientError as e:
            # TODO
            raise e
    elif ctx.message.attachments:
        return await from_attc()
    else:
        async for msg in ctx.channel.history(limit=10):
            if msg.attachments:
                return await from_attc()
