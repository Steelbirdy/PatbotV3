from typing import Optional, Tuple

from core import Context
from . import InfoObject, utils, format_fields
from .info_object2 import InfoObject2


class item_info(InfoObject):
    async def _as_markdown(self, ctx: Context):
        data = self.data
        name_mkd = f"**{data['name']}**"
        ret = f"*{description_fmt(data)}*\n"

        before, after = special_fmt(data)
        ret += before + '\n' if before else ''

        if 'value' in data:
            ret += f"{value_fmt(data)}\n"
        if utils.has_entries(data):
            ret += f"\n\u2800{utils.entries_mkd(data=data)}\n"

        ret += ('\n' + after + '\n') if after else ''

        if 'source' not in data:
            ret += f"\n**Source:** *{utils.source_mkd(data['inherits'])}*"
        else:
            ret += f"\n**Source:** *{utils.source_mkd(data)}*"
        format_from = data.get('inherits', {})
        format_from.update(data)
        ret = format_fields(ret, format_from)
        return name_mkd, ret


class item_info2(InfoObject2):
    @property
    def type(self):
        return utils.ITEM_TYPE_ABBREV_TO_NAME[self.data['type']]

    @property
    def rarity(self) -> Optional[str]:
        if self.data['rarity'] in {'none', 'unknown (magic)'}:
            return None
        else:
            return self.data['rarity']

    @property
    def attunement(self) -> Optional[str]:
        if 'reqAttune' not in self.data:
            return None
        elif self.data['reqAttune'] is True:
            return 'requires attunement'
        else:
            return f'requires attunement {self.data["reqAttune"]}'

    @property
    def is_weapon(self) -> bool:
        return self.data.get('weapon') is True or 'weaponCategory' in self.data

    @property
    def is_armor(self) -> bool:
        return 'ac' in self.data or self.data.get('armor') is True

    @property
    def is_wondrous(self) -> bool:
        return self.data.get('wondrous') is True

    @property
    def base_item(self) -> Optional[str]:
        base = self.data.get('baseItem')
        if base is None:
            return None
        count = base.count('|')
        if count == 2:
            return base.split('|')[-1]
        elif count == 1:
            return base.split('|')[0]
        else:
            return base

    def _weapon_markdown(self) -> str:
        data = self.data
        ret = "*"
        if data.get('staff') is True:
            ret += "Weapon (staff)"
        else:
            ret += f"{data['weaponCategory'].capitalize()} {self.type}"
        if 'baseItem' in data:
            ret += f" ({self.base_item})"

        if self.rarity is not None:
            ret += f", {self.rarity}"

        if self.attunement:
            ret += f" ({self.attunement})"
        ret += "*\n"

        line = ''
        props = None
        if 'dmg1' in data:
            line += f"{data['dmg1']} {utils.DAMAGE_TYPE_MAP[data['dmgType']]}"
            if 'property' in data:
                line += " — "
        if 'property' in data:
            props = list(map(lambda x: utils.WEAPON_PROPERTY_MAP[x], data['property']))
            temp = []
            for (name, _) in props:
                if name in {'ammunition', 'ammunition (futuristic)', 'thrown'}:
                    temp.append(f"{name} ({data['range']} ft.)")
                elif name == 'versatile':
                    temp.append(f"{name} ({data['dmg2']})")
                else:
                    temp.append(name)
            line += ", ".join(temp)
        ret += line.capitalize() + "\n"
        if 'value' in data:
            ret += value_fmt(data) + "\n"
        if 'entries' in data:
            ret += "\n" + utils.entries_mkd(data=data) + "\n"
        if props:
            ret += "\n**Properties**\n" + "\n".join(p[1] for p in props) + "\n"

        ret += "\n**Source:** *" + utils.source_mkd(data) + "*"
        return ret

    def _armor_markdown(self) -> str:
        data = self.data
        ret = "*"
        if self.type == 'shield':
            ret += "Armor (shield)"
        else:
            ret += f"{self.type.capitalize()}"

        if self.base_item is not None:
            ret += f" ({self.base_item})"
        if self.rarity is not None:
            ret += f", {self.rarity}"
        if self.attunement:
            ret += f" ({self.attunement})"
        ret += "*\n"

        if self.type == 'heavy armor':
            ret += f"AC {data['ac']}"
        elif self.type == 'medium armor':
            ret += f"AC {data['ac']} + Dex (max 2)"
        elif self.type == 'light armor':
            ret += f"AC {data['ac']} + Dex"
        elif self.type == 'shield':
            ret += f"AC +{data['ac']}"
        ret += "\n"

        if 'value' in data:
            ret += value_fmt(data) + "\n"
        if 'entries' in data:
            ret += "\n" + utils.entries_mkd(data=data) + "\n"

        if data.get('stealth') is True:
            ret += "\nThe wearer has disadvantage on Dexterity (Stealth) checks.\n"
        if 'strength' in data:
            ret += f"\nIf the wearer has a Strength score lower than {data['strength']}, " \
                    "their speed is reduced by 10 feet.\n"
        ret += f"\n**Source:** *{utils.source_mkd(data)}*"
        return ret

    def _wondrous_markdown(self):
        data = self.data
        ret = "*Wondrous item"

        if self.base_item:
            ret += f" ({self.base_item})"
        if self.rarity is not None:
            ret += f", {self.rarity}"
        if self.attunement is not None:
            ret += f" ({self.attunement})"
        ret += "*\n"

        if 'value' in data:
            ret += value_fmt(data) + "\n"

        if 'entries' in data:
            ret += f"\n{utils.entries_mkd(data=data)}\n"

        ret += f"\n**Source:** *{utils.source_mkd(data)}*"
        return ret

    def _other_markdown(self):
        data = self.data
        ret = f"*{self.type.capitalize()}"
        if self.base_item:
            ret += f" ({self.base_item})"

    def _name_body_markdown(self) -> Tuple[str, str]:
        data = self.data
        name = f"**{data['name']}**"
        if self.is_weapon:
            body = self._weapon_markdown()
        elif self.is_armor:
            body = self._armor_markdown()
        elif self.is_wondrous:
            body = self._wondrous_markdown()
        else:
            body = self._other_markdown()

        return name, body


def value_fmt(data: dict) -> str:
    value = int(data['value'])
    if value >= 100:
        return f"{value//100} gp"
    elif value >= 10:
        return f"{value//10} sp"
    else:
        return f"{value} cp"


def special_fmt(data: dict):
    if data.get('armor') is True:
        return armor_fmt(data)
    elif 'weaponCategory' in data:
        return weapon_fmt(data)
    else:
        return '', ''


def weapon_fmt(data: dict):
    properties = data.get('property', [])
    properties = [utils.WEAPON_PROPERTY_MAP[x] for x in properties]

    before, after = '', ''
    if 'dmg1' in data:
        damage_type = utils.DAMAGE_TYPE_MAP[data['dmgType']]
        before = f"{data['dmg1']} {damage_type} — "
    props = []
    afters = []
    for (name, desc) in properties:
        afters.append('\u2800' + desc)
        if 'ammunition' in name or name == 'thrown':
            props.append(f"{name} ({data['range']} ft.)")
        elif name == 'versatile':
            props.append(f"{name} ({data['dmg2']})")
        else:
            props.append(name)
    before += ', '.join(props)
    after += '\n'.join(afters)
    return before, after


def armor_fmt(data: dict):
    ac = data['ac']
    stealth = data.get('stealth')
    strength = data.get('strength')
    type = data.get('type')

    before = f'**AC:** {ac}'
    if type == 'LA':
        before += f' + Dex'
    elif type == 'MA':
        before += ' + Dex (max 2)'

    after = ''
    if stealth:
        after = 'The wearer has disadvantage on Dexterity (Stealth) checks.'
    if strength is not None:
        if stealth:
            after += '\n\n'
        after += f'If the wearer has a strength score lower than {strength}, their speed is reduced by 10 feet.'
    return before, after


def description_fmt(data: dict) -> str:
    wondrous = data.get('wondrous', False)
    type = data.get('type')
    if type is not None:
        type = utils.ITEM_TYPE_ABBREV_TO_NAME[type]

    if 'rarity' not in data:
        data = data['inherits']
    rarity = data['rarity']
    base_item = data.get('baseItem')
    if base_item is not None:
        if base_item.count('|') == 2:
            base_item = base_item.split('|')[-1]
        else:
            base_item = base_item.split('|')[0]
    attunement = data.get('reqAttune')

    ret = ''
    if wondrous:
        ret += "Wondrous item"
        if data.get('tattoo') is True:
            ret += " (tattoo)"
        elif type in {'spellcasting focus', 'instrument'}:
            ret += f" ({type})"
    elif data.get('weaponCategory') is not None or data.get('weapon') is True:
        ret += f"{data['weaponCategory']}"
        if data.get('staff') is True:
            ret += " melee weapon (staff)"
        else:
            ret += f" {type}"
            if base_item is not None:
                ret += f" ({base_item})"
    elif type == 'shield':
        ret += "Armor (shield)"
    else:
        ret += f"{type}"

    if rarity != 'none':
        ret += f", {rarity}"
    if attunement is True:
        ret += f" (requires attunement)"
    elif attunement is not None:
        ret += f" (requires attunement {attunement})"
    return ret.capitalize()
