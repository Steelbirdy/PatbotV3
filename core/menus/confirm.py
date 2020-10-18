from discord.ext import menus


class Confirm(menus.Menu):
    """
    A menu used for confirm/deny decisions that
    require verification.

    Usage Example
    ---------------

    .. code-block::

        @commands.command()
        async def delete_stuff(ctx):
            confirm = await Confirm('Delete everything?').prompt(ctx)
            if confirm:
                await ctx.send('deleted...')
    """

    def __init__(self, content: str, delete_message_after=True):
        super().__init__(timeout=30.0, delete_message_after=delete_message_after)
        self.content = content
        self.result = None

    async def send_initial_message(self, ctx, channel):
        return await channel.send(content=self.content)

    @menus.button('\N{WHITE HEAVY CHECK MARK}')
    async def on_confirm(self, payload):
        self.result = True
        self.stop()

    @menus.button('\N{CROSS MARK}')
    async def on_deny(self, payload):
        self.result = False
        self.stop()

    async def prompt(self, ctx):
        await self.start(ctx, wait=True)
        return self.result
