import discord
from discord.ext import commands
import json
import logging
import time

from core import Patbot


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    logging.info('Logging initialized.')

    with open("resources/auth.json", mode='r') as file:
        auth = json.load(file)
        logging.info('Loaded auth file.')

    bot = Patbot(auth=auth)

    bot.run(auth['login_token'])
