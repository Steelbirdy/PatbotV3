import discord
from discord.ext import commands


class PatbotError(Exception):
    pass


class PatbotCommandError(commands.CommandError):
    pass


class CogUnloadFailure(PatbotCommandError):
    def __init__(self, name: str):
        self.name = name
        super(CogUnloadFailure, self).__init__(f'The cog "{name}" failed to unload properly.')


class ConfigError(PatbotError):
    pass


class ConfigKeyError(ConfigError):
    def __init__(self, *path: str):
        super(ConfigKeyError, self).__init__('"' + '.'.join(path) + '"')


class ConfigUnregisteredDefault(ConfigKeyError):
    pass


class ConfigIllegalOperation(ConfigError):
    pass
