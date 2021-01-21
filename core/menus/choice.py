import discord
from discord.ext import menus


class SingleChoice(menus.Menu):
    def __init__(self, choices: list, content: str, delete_message_after: bool = True, message: discord.Message = None):
        super(SingleChoice, self).__init__(timeout=60.0, delete_message_after=delete_message_after,
                                           clear_reactions_after=True)
        self.choices = choices
        self.content = content
        self.my_message = message
        self.result: str = None
        self.generate_buttons()

    def button_fn(self, choice):
        async def inner(self, payload):
            self.result = choice
            self.stop()
        return inner

    def generate_buttons(self):
        self.choices = list(enumerate(self.choices))
        for (i, choice) in self.choices:
            self.add_button(menus.Button(emoji=f'{i+1}\N{COMBINING ENCLOSING KEYCAP}', action=self.button_fn(choice)))

        self.add_button(menus.Button(emoji=f'\N{CROSS MARK}', action=self.button_fn(None)))

    async def send_initial_message(self, ctx, channel):
        message = self.my_message
        if await ctx.accepts_embeds():
            embed = await ctx.default_embed(title=self.content)
            description = []
            for (i, choice) in self.choices:
                description.append(f'{i+1}\N{COMBINING ENCLOSING KEYCAP} :\u2800 {choice}')
            embed.description = '\n'.join(description)
            if message is not None:
                await message.edit(embed=embed)
                return message
            else:
                return await channel.send(embed=embed)
        else:
            content = self.content
            for (i, choice) in self.choices:
                content += f'\n\u2800{i+1}\N{COMBINING ENCLOSING KEYCAP} :\u2800 {choice}'
            if message is not None:
                await message.edit(content=content)
                return message
            else:
                return await channel.send(content=content)

    async def prompt(self, ctx):
        await self.start(ctx, wait=True)
        return self.result
