import re
from typing import Optional, Tuple, Union

from .utils import indent
from .fields import resolve_fields


def render_entries(data: dict = None, *, entries: list = None) -> str:
    entries = _get_entries(data, entries)
    entries = list(map(_render_entry, entries))
    # TODO


def _render_entry(entry: Union[dict, str], fix_fields: bool = True) -> Union[str, Tuple[str, dict]]:
    if isinstance(entry, str):
        ret = entry
    elif isinstance(entry, dict):
        etype = entry.get('type')
        fn_name = f'_render_{etype}_entry'
        if fn_name in locals():
            ret = locals()[fn_name](entry)
        else:
            raise ValueError(f"Unrecognized entry type flag `{etype}`")
    else:
        raise ValueError(f"Unrecognized entry type `{type(entry)}`")

    if fix_fields:
        ret = resolve_fields(ret)
    return ret


def _render_quote_entry(data: dict) -> str:
    sub_entries = data['entries']
    ret = f"> *\"{render_entries(entries=sub_entries)}\"*"

    signature = "— "
    L = len(signature)
    if 'by' in data:
        signature += data['by'] + ", " * ('from' in data)
    if 'from' in data:
        signature += f"*{data['from']}*"
    if len(signature) > L:
        ret += f"\n{indent(signature, level=2)}"

    return ret


def _render_list_entry(data: dict) -> str:
    items = map(_render_list_item, data['items'])
    return "\n".join(items)


def _render_list_item(item: Union[dict, str], indent_level=1) -> str:
    if isinstance(item, dict) and item['type'] == 'list':
        sub_items = map(lambda x: _render_list_item(x, indent_level=indent_level+1), item['items'])
        return "\n".join(sub_items)
    else:
        return indent("**•** ", level=indent_level) + _render_entry(item, resolve_fields=False)


def _get_entries(data, entries) -> Optional[list]:
    if entries is not None:
        return entries
    elif data is None:
        raise ValueError
    elif 'entries' in data:
        return data['entries']
    elif 'inherits' in data and 'entries' in data['inherits']:
        return data['inherits']['entries']
    else:
        raise ValueError
