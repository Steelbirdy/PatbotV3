from fuzzywuzzy import fuzz, process
from typing import List, Optional

from . import get_all_from_index, get_json


class Cache:
    def __init__(self):
        self._initialized = False
        self._caches = {
            'spell':
                'https://5e.tools/data/spells/index.json',
            'condition':
                'https://5e.tools/data/conditionsdiseases.json',
            'item': [
                ('https://5e.tools/data/items.json', 'item'),
                ('https://5e.tools/data/magicvariants.json', 'variant'),
                ('https://5e.tools/data/items-base.json', 'baseitem')
            ],
        }

    @property
    def initialized(self):
        return self._initialized

    def __getattr__(self, item):
        if item.endswith('_cache'):
            return self._caches[item[:-6]]
        elif item.endswith('_names'):
            return set(self._caches[item[:-6]].keys())
        elif item.startswith('get_'):
            if item.endswith('_fuzzy'):
                return lambda query: self._get_fuzzy(item[4:-6], query)
            else:
                return lambda query: self._get(item[4:], query)

    async def initialize(self, ignore_ua: bool = True):
        if self._initialized:
            return
        caches = dict()
        for k, v in self._caches.items():
            if isinstance(v, list):
                for (url, item) in v:
                    await self._add_json_to_cache(url, item, k, caches, ignore_ua=ignore_ua)
            else:
                await self._add_json_to_cache(v, k, k, caches, ignore_ua=ignore_ua)
        self._caches = caches
        self._initialized = True

    async def _add_json_to_cache(self, url: str, item: str, add_to: str, caches: dict, ignore_ua: bool = True):
        caches.setdefault(add_to, dict())
        if url.endswith('index.json'):
            temp = await get_all_from_index(url, ignore_ua=ignore_ua)
            caches[add_to].update({x['name'].lower().replace(' (generic)', ''): x
                                   for source in temp.values() for x in source[item]})
        else:
            temp = await get_json(url)
            caches[add_to].update({x['name'].lower().replace(' (generic)', ''): x
                                   for x in temp[item]})

    def _get(self, name: str, query: str) -> Optional[dict]:
        return self._caches[name].get(query.lower())

    def _get_fuzzy(self, name: str, query: str) -> List[str]:
        # scorer = fuzz.ratio if len(name.split(' ')) < 3 else fuzz.partial_ratio
        # picks = process.extract(query=query.lower(), choices=set(self._caches[name].keys()),
        #                         limit=4, scorer=scorer)
        query = query.lower()
        if query in self._caches[name]:
            return [query]

        choices = set(self._caches[name].keys())
        picks = dict(process.extract(query=query, choices=choices, limit=5, scorer=fuzz.ratio))
        for (name, val) in process.extract(query=query, choices=choices, limit=5, scorer=fuzz.partial_ratio):
            picks[name] = max(picks.get(name, 0), val)
        return sorted(picks.keys(), key=lambda x: -picks[x])[:4]
