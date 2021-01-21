import aiohttp


async def get_json(url: str) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.json()


async def get_all_from_index(url: str, ignore_ua: bool = True) -> dict:
    if url.endswith('/index.json'):
        url = url[:-len('index.json')]
    index = await get_json(url + 'index.json')

    if ignore_ua:
        index = {k: v for k, v in index.items() if not k.startswith('UA') and not v.startswith('UA')}

    index = {k: await get_json(url + v) for k, v in index.items()}
    return index


async def main(url):
    data = await get_all_from_index(url)
    print('\n'.join(f'{k}: {len(v["spell"])}' for k, v in data.items()))


if __name__ == '__main__':
    import asyncio
    asyncio.run(main('https://5e.tools/data/spells/index.json'))
