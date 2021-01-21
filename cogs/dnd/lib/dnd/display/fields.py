import re
from typing import Optional, Tuple


_STYLE_MAP = {
    'b': lambda x: f"**{x}**",
    'i': lambda x: f"*{x}*",
    'n': lambda x: f"*`{x}`*",
    's': lambda x: f"~~{x}~~",
    'u': lambda x: f"__{x}__",
}
_FIELD_PATTERN = re.compile(r'{@(\w+) ([^}]+?}*)}')
_FIELD_TYPES = {
    'style': {'b', 'bold', 'i', 'italic', 'n', 'note', 's', 'strike', 'u', 'underline'},
    'roll': {'dice', 'hit', 'damage', 'd20', 'scaledice'},
}


def resolve_fields(text: str, *, compact=False) -> Tuple[str, list]:
    text = _resolve_style_fields(text, no_style=compact)
    found = list()
    for match in _FIELD_PATTERN.finditer(text):
        pass  # TODO


def _resolve_style_fields(text: str, *, no_style=False, **ignore) -> str:
    to_ignore = {k[0].lower() for k in ignore if ignore[k] is True}
    for match in _FIELD_PATTERN.finditer(text):
        ftype = match[1].lower()
        if ftype not in _FIELD_TYPES['style']:
            continue

        fval = match[2]
        new = _resolve_style_fields(fval, no_style=no_style, **ignore)
        if not no_style and ftype not in to_ignore:
            fn = _STYLE_MAP[ftype[0]]
            new = fn(new)
        text = text.replace(match[0], new)
    return text


def _resolve_roll_field(match: re.Match, *, compact=False) -> Tuple[str, Optional[dict]]:
    ftype, fval = match[1].lower(), match[2]

    if ftype in {'dice', 'damage'}:
        return _parse_dice_field(fval, compact=compact)
    elif ftype in {'hit', 'd20'}:
        return _parse_roll_bonus(fval, compact=compact)
    elif ftype in {'scaledice'}:
        return _parse_scaledice(fval, compact=compact)
    else:
        raise ValueError(f'Unhandled dice field tag {ftype}')


def _parse_dice_field(text: str, compact: bool) -> Tuple[str, dict]:
    data = {
        'type': 'roll',
    }
    query = text

    if '#$' in text:
        # prompts = []
        # i = 0
        query = None  # Currently don't support rolling dice that needs input
        while '#$' in text:
            start, end = text.index('#$'), text.index('$#')
            # substring = text[start+2:end]
            # p, d = _parse_prompt(substring)
            # text = text[:start] + p + text[end+2:]
            text = text[:start] + '(n)' + text[end+2:]
            # prompts.append(d)

            # q_start, q_end = query.index('#$'), query.index('$#')
            # query = query[:q_start] + query[q_end+2:]
            # i += 1
        # data['prompts'] = prompts

    data['query'] = query

    if not compact:
        text = f"`{text}`"
    return text, data


# def _parse_prompt(text: str) -> Tuple[str, dict]:
#     ptype = text[7:text.index(':')]
#     if ptype == 'number':
#         return _parse_number_prompt(text[text.index(':')+1:])
#     else:
#         raise ValueError(f'Unrecognized prompt type: `{ptype}`')
#
#
# def _parse_number_prompt(text: str) -> Tuple[str, dict]:
#     data = {
#         'title': 'Enter a Number',
#         'default': 0,
#     }
#     data.update(x.split('=') for x in text.split(','))
#
#     int_props = {'default', 'min', 'max'}
#     for p in int_props:
#         if p in data:
#             data[p] = int(data[p])
#     return "(n)", data


def _parse_roll_bonus(text: str, compact: bool) -> Tuple[str, dict]:
    ret = "1d20"
    text = text.strip()
    if text.startswith('-'):
        ret += f" - {text[1:]}"
    elif text.startswith('+'):
        ret += f" + {text[1:]}"
    else:
        ret += f" + {text}"

    data = {
        'type': 'roll',
        'query': ret,
    }
    if not compact:
        ret = f"`{ret}`"
    return ret, data


def _parse_scaledice(text: str, compact: bool) -> Tuple[str, dict]:
    pass  # TODO
