from typing import Optional, Tuple

from core.formatting import humanize_list as pretty_list
from core import Context
from . import InfoObject, utils
from .info_object2 import InfoObject2


class spell_info(InfoObject):
    async def _as_markdown(self, ctx: Context) -> Tuple[str, str]:
        data = self.data
        name_mkd = f'**{data["name"]}**'
        ret = f"*{level_school_ritual_mkd(data)}*\n" \
              f"**Casting Time:** {casting_time_mkd(data)}\n" \
              f"**Range:** {range_mkd(data)}\n" \
            +(f"**Components:** {components_mkd(data)}\n" if 'components' in data else "") \
            + f"**Duration:** {duration_mkd(data)}\n\n" \
              f"{utils.entries_mkd(data=data)}\n\n" \
            +(f"{entries_higher_level_mkd(data)}\n\n" if 'entriesHigherLevel' in data else "") \
            + f"**Source:** *{utils.source_mkd(data)}*"
        return name_mkd, ret


class spell_info2(InfoObject2):
    def __init__(self, data):
        super(spell_info2, self).__init__(data=data)

    def __name_body_markdown(self) -> Tuple[str, str]:
        data = self.data
        name = f'**{data["name"]}**'
        body = f"*{level_school_ritual_mkd(data)}*\n" \
               f"**Casting Time:** {casting_time_mkd(data)}\n" \
               f"**Range:** {range_mkd(data)}\n" \
               f"**Components:** {components_mkd(data)}\n" if 'components' in data else "" \
               f"**Duration:** {duration_mkd(data)}\n" \
               f"\n{utils.entries_mkd(data=data)}\n" \
               f"\n{entries_higher_level_mkd(data)}\n" if 'entriesHigherLevel' in data else "" \
               f"\n**Source:** *{utils.source_mkd(data)}*"
        return name, body


def level_school_ritual_mkd(data: dict) -> str:
    level: str = utils.number_to_level(data['level'])
    school: str = utils.school_abbrev_to_name(data['school'])
    is_ritual: bool = data.get('meta', {}).get('ritual', False)
    if level == 'cantrip':
        ret = f'{school.capitalize()} cantrip'
    else:
        ret = f'{level} {school}{" (ritual)" if is_ritual else ""}'
    return ret


def casting_time_mkd(data: dict) -> str:
    data = data['time']
    if isinstance(data, list):
        data = data[0]
    number: int = data.get('number')
    unit: str = data['unit']
    condition: str = data.get('condition')

    ret = ''
    if number is None:
        ret += unit.capitalize()
    else:
        ret += f'{number} {unit}{"" if number == 1 else "s"}'
    if condition is not None:
        ret += ', ' + condition
    return ret


def range_mkd(data: dict) -> str:
    data = data['range']
    type: str = data['type']
    distance: dict = data.get('distance')

    ret = ''
    if type != 'point':
        ret += 'Self ('
        dist_type = distance['type']
        amount: int = distance.get('amount')
        if dist_type == 'feet':
            dist_type = 'foot'
        elif dist_type.endswith('s'):
            dist_type = dist_type[:-1]
        ret += f'{amount}-{dist_type} {type})'
    elif distance is None:
        ret += type.capitalize()
    else:
        type = distance['type']
        amount: int = distance.get('amount')
        if amount is None:
            ret += type.capitalize()
        else:
            if amount == 1:
                if type == 'feet':
                    type = 'foot'
                elif type == 'miles':
                    type = 'mile'
            ret += f'{amount} {type}'
    return ret


def components_mkd(data: dict) -> Optional[str]:
    if 'components' not in data:
        return
    data = data['components']
    v: bool = data.get('v', False)
    s: bool = data.get('s', False)
    m = data.get('m')

    ret = ''
    temp = []
    if v is True:
        temp.append('V')
    if s is True:
        temp.append('S')
    if m is not None:
        if m is True:
            temp.append('M')
        elif isinstance(m, str):
            temp.append(f'M ({m})')
        else:
            temp.append(f'M ({m["text"]})')
    ret += ', '.join(temp)
    return ret


def duration_mkd(data: dict) -> str:
    data = data['duration']
    if isinstance(data, list):
        data = data[0]
    type: str = data['type']

    ret = ''
    if type == 'instant':
        ret += 'Instantaneous'
    elif type == 'timed':
        duration = data['duration']
        type = duration['type']
        amount: int = duration.get('amount')
        concentration: bool = data.get('concentration', False)
        up_to: bool = duration.get('upTo', False) or concentration
        temp = ''
        if concentration:
            temp += 'concentration, '
        if up_to:
            temp += 'up to '
        if amount is None:
            temp += type
        else:
            temp += f'{amount} {type}{"" if amount == 1 else "s"}'
        ret += temp[0].capitalize() + temp[1:]
    elif type == 'permanent':
        ends: list = data.get('ends')
        if not ends:
            ret += 'Permanent'
        else:
            ends = [(x + 'led') if x == 'dispel' else (x + 'ed') for x in ends]
            ret += f'Until {pretty_list(ends, end_word="or")}'
    elif type == 'special':
        ret += 'Special'
    return ret


def entries_higher_level_mkd(data: dict) -> Optional[str]:
    if 'entriesHigherLevel' in data:
        return utils.entries_mkd(entries=data['entriesHigherLevel'], indent_first=True)
