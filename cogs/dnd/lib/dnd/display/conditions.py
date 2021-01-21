from typing import Tuple

from core import Context
from . import InfoObject, utils
from .info_object2 import InfoObject2


class condition_info(InfoObject):
    async def _as_markdown(self, ctx: Context):
        data = self.data
        name_mkd = f'**{data["name"]}**'
        ret = f'{utils.entries_mkd(data=data)}\n\n' \
              f'**Source:** *{utils.source_mkd(data)}*'
        return name_mkd, ret


class condition_info2(InfoObject2):
    def __name_body_markdown(self) -> Tuple[str, str]:
        data = self.data
        name = f"**{data['name']}**"
        body = f"{utils.entries_mkd(data=data)}\n" \
               f"\n**Source:** *{utils.source_mkd(data)}*"
        return name, body
