import json
import logging
import sys

from core import Patbot


if __name__ == '__main__':
    args = sys.argv[1:]
    logging.basicConfig(level=logging.INFO)
    logging.info('Logging initialized.')

    with open("resources/auth.json", mode='r') as file:
        auth = json.load(file)
        logging.info('Loaded auth file.')

    bot = Patbot(auth=auth)

    if 'testing' in args:
        login_token = auth['test_login_token']
        bot._testing = True
    else:
        login_token = auth['login_token']

    bot.run(login_token)
