import asyncio
import discord
from discord.ext import commands
import json
import logging
import os
from pathlib import Path
import pickle
from typing import Any, AsyncContextManager, Awaitable, Dict, Optional, Sequence, Union

from core import errors

__all__ = ["Config"]


class _ValueContextManager(AsyncContextManager, Awaitable):
    def __init__(self, value_obj: "Value", coroutine: Awaitable[Any]):
        self.value_obj = value_obj
        self.coroutine = coroutine
        self._raw_value = None
        self.__original_value = None
        self.__lock: asyncio.Lock = self.value_obj.get_lock()

    def __await__(self):
        return self.coroutine.__await__()

    async def __aenter__(self):
        await self.__lock.acquire()
        self._raw_value = await self
        if not isinstance(self._raw_value, (dict, list)):
            raise errors.ConfigIllegalOperation('Context manager value must be mutable.')
        self.__original_value = deepcopy(self._raw_value)
        return self._raw_value

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        try:
            if isinstance(self._raw_value, dict):
                raw = keys_to_str(self._raw_value)
            else:
                raw = self._raw_value
            if raw != self.__original_value:
                await self.value_obj.set(self._raw_value)
        finally:
            self.__lock.release()


class Value:
    def __init__(self, path: Sequence[str], config: "Config", default=None):
        self._path = path
        self._config = config
        self._default = default

    @property
    def default(self):
        return deepcopy(self._default)

    def __call__(self) -> _ValueContextManager:
        return _ValueContextManager(self, self._get())

    def get_lock(self) -> asyncio.Lock:
        return self._config._get_lock(*self._path)

    async def _get(self) -> Any:
        ret = await self._config._get(*self._path)
        if ret is None:
            return self.default
        else:
            return ret

    async def set(self, value: Any):
        if isinstance(value, dict):
            value = keys_to_str(value)
        await self._config._set(*self._path, value=value)

    async def clear(self):
        await self._config._clear(*self._path)


class Group(Value):
    def __init__(self, path: Sequence[str], config: "Config", defaults: Dict[str, Any] = None):
        super(Group, self).__init__(path, config, {})
        self._defaults = defaults

    @property
    def default(self) -> Dict[str, Any]:
        return deepcopy(self._defaults)

    defaults = default

    def __getattr__(self, item: str) -> Value:
        is_group = self._is_group(item)
        is_value = not is_group and self._is_value(item)
        new_path = [*self._path, item]
        if is_group:
            return Group(new_path, self._config, self._defaults[item])
        elif is_value:
            return Value(new_path, self._config, self._defaults[item])
        else:
            self._config.log.warning(f'Could not determine whether {".".join(self._path)}.{item} was a group or value.')
            return Value(new_path, self._config)

    def __getitem__(self, item):
        return self.__getattr__(str(item))

    def _is_group(self, item: str) -> bool:
        default = self._defaults.get(str(item))
        return isinstance(default, dict)

    def _is_value(self, item: str) -> bool:
        try:
            default = self._defaults[str(item)]
        except KeyError:
            return False
        else:
            return not isinstance(default, dict)

    async def _get(self) -> Dict[str, Any]:
        raw = await super(Group, self)._get()
        if isinstance(raw, dict):
            return self.nested_update(raw, self.defaults)
        else:
            return raw

    async def set(self, value: Dict[str, Any]):
        if not isinstance(value, dict):
            raise errors.ConfigIllegalOperation('Failed to set value of a group to a non-dictionary object.')
        await super(Group, self).set(value)

    def nested_update(self, current: Dict[str, Any], defaults: Dict[str, Any]) -> Dict[str, Any]:
        for key, value in current.items():
            if isinstance(value, dict):
                result = self.nested_update(value, defaults.get(key, {}))
                defaults[key] = result
            else:
                defaults[key] = deepcopy(current[key])
        return defaults


class _ConfigMeta(type):
    _cache_log = logging.getLogger('config.cache')
    _cache_log.setLevel(logging.DEBUG)

    _config_cache = {}

    def __call__(cls, cog_name: str):
        if cog_name is None:
            raise errors.ConfigIllegalOperation(
                'You must provide a cog name when instantiating or getting a config.')

        if cog_name in cls._config_cache:
            cls._cache_log.debug(f'Found cached Config object for cog `{cog_name}`')
            return cls._config_cache[cog_name]

        cls._cache_log.debug(f'Creating new Config instance for cog `{cog_name}`')
        inst = super(_ConfigMeta, cls).__call__(cog_name)
        cls._config_cache[cog_name] = inst
        return inst


class Config(metaclass=_ConfigMeta):
    _cogs_root_path = 'cogs'
    COG_SETTINGS = 'COG_SETTINGS'
    GLOBAL = 'GLOBAL'
    GUILD = 'GUILD'
    TEXTCHANNEL = 'TEXTCHANNEL'
    VOICECHANNEL = 'VOICECHANNEL'
    ROLE = 'ROLE'

    def __init__(self, cog_name: str):
        self.cog_name = cog_name
        self.log = logging.getLogger(cog_name + '.config')
        self._data = None
        self._data_path = Path(self._cogs_root_path, cog_name, 'config.json')
        self._defaults = {
            self.GLOBAL: {},
            self.GUILD: {},
            self.TEXTCHANNEL: {},
            self.VOICECHANNEL: {},
            self.ROLE: {},
        }
        self._locks = {}
        self._lock = asyncio.Lock()
        self._load_data()

    @property
    def defaults(self):
        return deepcopy(self._defaults)

    def __getattr__(self, item: str):
        _global_group = self._get_category(self.GLOBAL)
        return getattr(_global_group, item)

    def _load_data(self):
        with self._data_path.open(mode='r', encoding='utf-8') as file:
            self._data = json.load(file)

    def _get_lock(self, *path: str) -> asyncio.Lock:
        partial = self._locks
        for d in path:
            partial = partial.setdefault(d, {})
        if None not in partial:
            partial[None] = asyncio.Lock()
        return partial[None]

    async def _get_default(self, *path: str) -> Any:
        partial = self._defaults
        try:
            for d in path:
                partial = partial[d]
        except KeyError:
            raise errors.ConfigUnregisteredDefault(*path)
        return deepcopy(partial)

    async def _get(self, *path: str) -> Any:
        partial = self._data
        try:
            for d in path:
                partial = partial[d]
            return deepcopy(partial)
        except KeyError:
            return None

    async def _set(self, *path: str, value: Any):
        partial = self._data
        value_copy = json.loads(json.dumps(value))
        async with self._lock:
            try:
                for p in path[:-1]:
                    partial = partial.setdefault(p, {})
                partial[path[-1]] = value_copy
                await self._save()
            except AttributeError:
                raise errors.ConfigIllegalOperation(f'Failed to change {self.cog_name}.{".".join(path)}".')

    async def _clear(self, *path: str):
        partial = self._data
        for p in path[:-1]:
            try:
                partial = partial[p]
            except KeyError:
                return
        async with self._lock:
            try:
                del partial[path[-1]]
            except KeyError:
                return
            await self._save()

    async def _save(self):
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, save_json, self._data_path, self._data)

    @classmethod
    def get_config(cls, cog_name: str = None, cog_instance: commands.Cog = None) -> "Config":
        if cog_name is None:
            if cog_instance is None:
                raise errors.ConfigIllegalOperation('You must provide either a cog name or instance.')
            cog_name = type(cog_instance).__name__
        return cls(cog_name.lower())

    @classmethod
    def core_config(cls) -> "Config":
        return cls.get_config(cog_name="core")

    def _get_category(self, name: str, key: Optional[str] = None) -> Group:
        identifier = [name] if key is None else [name, key]
        if key is None and name is not self.GLOBAL:
            return Group(identifier, self, {})
        return Group(identifier, self, self._defaults[name])

    def _register_defaults(self, category: str, **values):
        partial = self._defaults
        data = deepcopy(values)

        partial = partial.setdefault(category, {})
        for k, v in data.items():
            split = k.split('__')
            tmp = partial
            for d in split[:-1]:
                tmp = tmp.setdefault(d, {})
            tmp[split[-1]] = v
            self.log.debug(f'Registered `{v}` for `{".".join([category] + split)}`.')

    def register_global(self, **values):
        self._register_defaults(self.GLOBAL, **values)

    def register_guild(self, **values):
        self._register_defaults(self.GUILD, **values)

    def register_textchannel(self, **values):
        self._register_defaults(self.TEXTCHANNEL, **values)

    def register_voicechannel(self, **values):
        self._register_defaults(self.VOICECHANNEL, **values)

    def register_role(self, **values):
        self._register_defaults(self.ROLE, **values)

    def register_custom(self, name: str, **values):
        if name in (self.GLOBAL, self.GUILD, self.TEXTCHANNEL, self.VOICECHANNEL, self.ROLE):
            raise errors.ConfigIllegalOperation('Use the correct method to register default values.')
        self._register_defaults(name, **values)

    def init_custom(self, name: str):
        self._data.setdefault(name, {})

    @property
    def cog_settings(self) -> Group:
        return self._get_category(self.COG_SETTINGS)

    def guild(self, source: Union[int, discord.Guild, commands.Context]) -> Group:
        if isinstance(source, commands.Context):
            if not source.guild:
                raise errors.ConfigIllegalOperation('The context object does not have an associated guild.')
            source = source.guild.id
        elif isinstance(source, discord.Guild):
            source = source.id
        return self._get_category(self.GUILD, str(source))

    def textchannel(self, source: Union[int, discord.TextChannel, commands.Context]) -> Group:
        if isinstance(source, commands.Context):
            source = source.channel.id
        elif isinstance(source, discord.TextChannel):
            source = source.id
        return self._get_category(self.TEXTCHANNEL, str(source))

    def voicechannel(self, source: Union[int, discord.VoiceChannel, discord.Member]) -> Group:
        if isinstance(source, discord.Member):
            if source.voice.channel:
                source = source.voice.channel.id
            else:
                raise errors.ConfigIllegalOperation('The member is not in a voice channel.')
        elif isinstance(source, discord.VoiceChannel):
            source = source.id
        return self._get_category(self.VOICECHANNEL, str(source))

    def role(self, source: Union[int, discord.Role]) -> Group:
        if isinstance(source, discord.Role):
            source = source.id
        return self._get_category(self.ROLE, str(source))

    def custom(self, name: str) -> Group:
        if name in (self.GLOBAL, self.GUILD, self.TEXTCHANNEL):
            raise errors.ConfigIllegalOperation('Use the correct method to get a Group.')
        return self._get_category(name)

    def guilds(self) -> Group:
        return self._get_category(self.GUILD)

    def textchannels(self) -> Group:
        return self._get_category(self.TEXTCHANNEL)

    def voicechannels(self) -> Group:
        return self._get_category(self.VOICECHANNEL)

    def roles(self) -> Group:
        return self._get_category(self.ROLE)

    async def _ctx_default(self, ctx: Union[commands.Context, discord.Message], *path: str) -> Any:
        if not ctx.guild:
            return await self._get_default(self.GLOBAL, *path)
        paths = (self.TEXTCHANNEL, self.GUILD, self.GLOBAL)
        for p in paths:
            try:
                ret = await self._get_default(p, *path)
            except errors.ConfigUnregisteredDefault:
                continue
            else:
                if ret is not None:
                    return ret
        return None

    async def from_ctx(self, ctx: Union[commands.Context, discord.Message], *path: str) -> Any:
        if not ctx.guild:
            return await self._get(self.GLOBAL, *path) or await self._ctx_default(ctx, *path)
        paths = (
            # (self.TEXTCHANNEL, str(ctx.channel.id)),
            (self.GUILD, str(ctx.guild.id)),
            (self.GLOBAL,)
        )
        for p in paths:
            try:
                ret = await self._get(*p, *path)
            except errors.ConfigKeyError:
                continue
            if ret is not None:
                return ret
        return await self._ctx_default(ctx, *path)


def save_json(path: Path, data: Dict[str, Any]):
    filename = path.stem
    tmp_file = f'{filename}.tmp'
    tmp_path = path.parent / tmp_file
    with tmp_path.open(mode='w', encoding='utf-8') as file:
        json.dump(data, file, indent='\t')
        file.flush()
        os.fsync(file.fileno())
    tmp_path.replace(path)
    try:
        flag = os.O_DIRECTORY
    except AttributeError:
        pass
    else:
        fd = os.open(path.parent, flag)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def keys_to_str(d: Dict[Any, Any]) -> Dict[str, Any]:
    tr = {}
    for k, v in d.items():
        if isinstance(v, dict):
            v = keys_to_str(v)
        tr[str(k)] = v
    return tr


def deepcopy(o):
    return pickle.loads(pickle.dumps(o, -1))
