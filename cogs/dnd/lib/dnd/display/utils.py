from . import remove_fields, tables
from core.formatting import split_text

__all__ = [
    'number_to_level',
    'school_abbrev_to_name',
    'add_backticks_as_needed',
]


WEAPON_PROPERTY_MAP = {
    'T': ('thrown', '***Thrown.*** If a weapon has the thrown property, you can throw the weapon to make a ranged '
                    'attack. If the weapon is a melee weapon, you use the same ability modifier for that attack roll '
                    'and damage roll that you would use for a melee attack with the weapon. For example, if you throw a'
                    ' *handaxe*, you use your Strength, but if you throw a *dagger*, you can use either your Strength '
                    'or your Dexterity, since the *dagger* has the finesse property.'),
    'V': ('versatile', '***Versatile.*** This weapon can be used with one or two hands. A damage value in parentheses '
                       'appears with the property — the damage when the weapon is used with two hands to make a melee '
                       'attack.'),
    'H': ('heavy', "***Heavy.*** Creatures that are Small or Tiny have disadvantage on attack rolls with heavy weapons."
                   " A heavy weapon's size and bulk make it too large for a Small or Tiny creature to use effectively."
          ),
    '2H': ('two-handed', "***Two-Handed.*** This weapon requires two hands to use. This property is relevant only when "
                         "you attack with the weapon, not when you simply hold it."),
    'F': ('finesse', "***Finesse.*** When making an attack with a finesse weapon, you use your choice of your Strength "
                     "or Dexterity modifier for the attack and damage rolls. You must use the same modifier for both "
                     "rolls."),
    'L': ('light', "***Light.*** A light weapon is small and easy to handle, making it ideal for use when fighting with"
                   " two weapons."),
    'R': ('reach', "***Reach.*** This weapon adds 5 feet to your reach when you attack with it. This property also "
                   "determines your reach for opportunity attacks with a reach weapon."),
    'A': ('ammunition', "***Ammunition.*** You can use a weapon that has the ammunition property to make a ranged "
                        "attack only if you have ammunition to fire from the weapon. Each time you attack with the "
                        "weapon, you expend one piece of ammunition. Drawing the ammunition from a quiver, case, or "
                        "other container is part of the attack. Loading a one-handed weapon requires a free hand. At "
                        "the end of the battle, you can recover half your expended ammunition by taking a minute to "
                        "search the battlefield.\n\u2800If you use a weapon that has the ammunition property to make a "
                        "melee attack, you treat the weapon as an improvised weapon. A *sling* must be loaded to deal "
                        "any damage when used in this way."),
    'LD': ('loading', "***Loading.*** Because of the time required to load this weapon, you can fire only one piece of"
                      " ammunition from it when you use an action, bonus action, or reaction to fire it, regardless of"
                      " the number of attacks you can normally make."),
    'S': ('special', ""),
    'AF': ('ammunition (futuristic)',
           "***Ammunition.*** You can use a weapon that has the ammunition property to make a ranged attack only if you"
           " have ammunition to fire from the weapon. Each time you attack with the weapon, you expend one piece of "
           "ammunition. Drawing the ammunition from a quiver, case, or other container is part of the attack. Loading a"
           " one-handed weapon requires a free hand. The ammunition of a firearm is destroyed upon use.\n\u2800If you "
           "use a weapon that has the ammunition property to make a melee attack, you treat the weapon as an improvised"
           " weapon. A *sling* must be loaded to deal any damage when used in this way."),
    'RLD': ('reload', "***Reload.*** A limited number of shots can be made with a weapon that has the reload property. "
                      "A character must then reload it using an action or a bonus action (the character's choice)."),
    'BF': ('burst fire', "***Burst Fire.*** A weapon that has the burst fire property can make a single-target attack, "
                         "or it can spray a 10-foot-cube area within normal range with shots. Each creature in the area"
                         " must succeed on a DC 15 Dexterity saving throw or take the weapon's normal damage. This "
                         "action uses ten pieces of ammunition."),
}


DAMAGE_TYPE_MAP = {
    'A': 'acid',
    'B': 'bludgeoning',
    'C': 'cold',
    'F': 'fire',
    'O': 'force',
    'L': 'lightning',
    'N': 'necrotic',
    'P': 'piercing',
    'I': 'poison',
    'Y': 'psychic',
    'R': 'radiant',
    'S': 'slashing',
    'T': 'thunder',
}


SCHOOL_ABBREV_TO_NAME_MAP = {
    'A': 'abjuration',
    'V': 'evocation',
    'E': 'enchantment',
    'I': 'illusion',
    'D': 'divination',
    'N': 'necromancy',
    'T': 'transmutation',
    'C': 'conjuration',
    'P': 'psionic',
}

NUMBER_TO_SPELL_LEVEL_MAP = {
    0: 'cantrip',
    1: '1st-level',
    2: '2nd-level',
    3: '3rd-level',
}


ITEM_TYPE_ABBREV_TO_NAME = {
    'A': 'ammunition',
    'AF': 'ammunition (futuristic)',
    'AT': 'artisan tool',
    'EM': 'elditch machine',
    'EXP': 'explosive',
    'G': 'adventuring gear',
    'GS': 'gaming set',
    'HA': 'heavy armor',
    'INS': 'instrument',
    'LA': 'light armor',
    'M': 'melee weapon',
    'MA': 'medium armor',
    'MNT': 'mount',
    'GV': 'generic variant',
    'P': 'potion',
    'R': 'ranged weapon',
    'RD': 'rod',
    'RG': 'ring',
    'S': 'shield',
    'SC': 'scroll',
    'SCF': 'spellcasting focus',
    'OTH': 'other',
    'T': 'tool',
    'TAH': 'tack and harness',
    'TG': 'trade good',
    '$': 'treasure',
    'VEH': 'vehicle (land)',
    'SHP': 'vehicle (water)',
    'AIR': 'vehicle (air)',
    'WD': 'wand',
}


def school_abbrev_to_name(abbrev: str) -> str:
    return SCHOOL_ABBREV_TO_NAME_MAP.get(abbrev, '[Unknown school]')


def number_to_level(n: int) -> str:
    return NUMBER_TO_SPELL_LEVEL_MAP.get(n, f'{n}th-level')


MESSAGE_CHAR_LIMIT = 2000
EMBED_CHAR_LIMIT = 2048


def split_content(content: str, limit: int = MESSAGE_CHAR_LIMIT) -> list:
    ret = []
    add_to_next = False
    for block in split_text(content, limit=limit - 3):
        if add_to_next is True:
            block = '```' + block
            add_to_next = False
        if block.count('```') % 2:
            block += '```'
            add_to_next = True
        ret.append(block)
    return ret


def add_backticks_as_needed(texts: list) -> list:
    add_to_next = False
    ret = []
    for t in texts:
        if add_to_next:
            t = '```' + t
            add_to_next = False
        if t.count('```') % 2:
            t += '```'
            add_to_next = True
        ret.append(t)
    return ret


def has_entries(data: dict) -> bool:
    return 'entries' in data or 'entries' in data.get('inherits', {})


def entries_mkd(*, data: dict = None, entries: list = None, indent_first: bool = False, no_indent: bool = False) -> str:
    if (data or entries) is None:
        raise ValueError()
    entries: list = entries or data.get('entries') or data.get('inherits', {}).get('entries')
    return '\n'.join(map(lambda y: (lambda i, x: entry_mkd(x, indent=(i or indent_first) and not no_indent))(*y),
                         enumerate(entries))).replace('```\n\n', '```\n').strip('\n')


def entry_mkd(entry, indent: bool = False) -> str:
    if isinstance(entry, str):
        return '\u2800' * indent + remove_fields(entry)
    elif isinstance(entry, dict):
        type = entry['type']
        if type == 'entries':
            name = entry['name']
            entries = entry['entries']
            return f'***{name}.*** {entries_mkd(entries=entries, no_indent=True)}'
        elif type == 'table':
            return '\n' + tables.format_table2(**entry)
        elif type == 'list':
            add_bullet = lambda x: f'**•**\u2800{x}'
            return '\n' + entries_mkd(entries=list(map(add_bullet, entry['items'])), no_indent=True) + '\n'
        else:
            return f"**!! I don't currently support displaying {type} entries.**"
    else:
        raise TypeError(f'Unrecognized entry of type {entry.__class__}: {list(entry.keys())}')


def source_mkd(data: dict) -> str:
    source = data['source']
    page = data.get('page')
    ret = source.upper()
    if page is not None:
        ret += f', page {page}'
    return ret


def indent(text: str, level: int = 1) -> str:
    return '\u2800' * level + text
