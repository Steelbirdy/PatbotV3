from . import remove_fields
import textwrap
import unittest


MAX_ROW_LENGTH = 61


def format_table2(*, colLabels: list, colStyles: list, rows: list, caption: str = None, **kwargs) -> str:
    labels, styles = colLabels, colStyles
    L = len(labels)
    labels = list(map(remove_fields, labels))
    table = [parse_row(labels)]
    table.extend(map(parse_row, rows))

    styles = parse_styles(styles)
    longest_per_column = [max(table, key=lambda x: len(x[col]))[col] for col in range(L)]
    widths = [min(styles[i][0], len(longest_per_column[i])) for i in range(L)]
    spacing = max(2, min(4, (MAX_ROW_LENGTH - 1 - sum(widths)) // (L - 1)))
    line_spacer = '\n' + ('-' * min(MAX_ROW_LENGTH, sum(widths) + spacing * L))
    widths[-1] = MAX_ROW_LENGTH - (sum(widths[:-1]) + spacing * (L - 1))

    table = split_rows(table, widths)
    styles = [f'{{:{styles[i][1]}{widths[i]}}}' for i in range(L)]

    ret = f'**{caption}**```' if caption else '```'
    ret += '\n' + (' ' * spacing).join(styles[i].format(table[0][i]) for i in range(L))
    # ret += '\n' + ('-' * (sum(widths) + spacing * (L - 1)))
    for row in table[1:]:
        if row[0] is True:
            row = row[1:]
            ret += line_spacer
        ret += '\n' + (' ' * spacing).join(styles[i].format(row[i].lstrip(' ')) for i in range(L))
    ret = ret.rstrip() + '```'
    return ret


def split_rows(table, widths) -> list:
    ret = []
    for i, row in enumerate(table):
        if all(len(row[c]) <= widths[c] for c in range(len(widths))):
            if i != 0:
                row.insert(0, True)
            ret.append(row)
            continue

        row_split = [textwrap.wrap(row[c], width=widths[c]) for c in range(len(widths))]
        h = max(map(len, row_split))
        for j in range(h):
            subrow = [True] if i != j == 0 else []
            for cell in row_split:
                subrow.append(cell[j] if len(cell) > j else '')
            ret.append(subrow)
    return ret


def parse_styles(styles: list) -> list:
    ret = []
    for style in styles:
        style = style.split(' ')
        max_width = int(style[0][4:]) * 5
        if len(style) == 2:
            align = style[1]
        else:
            align = 'text-left'
        if align == 'text-left':
            align = '<'
        elif align == 'text-center':
            align = '^'
        elif align == 'text-right':
            align = '>'
        else:
            raise ValueError(f'Invalid alignment attribute {style[1]}')
        ret.append((max_width, align))
    return ret


def format_table(entry: dict) -> str:
    labels = entry['colLabels']
    L = len(labels)
    styles = entry['colStyles']
    rows = entry['rows']
    caption = entry['caption']
    labels = list(map(remove_fields, labels))
    table = [parse_row(labels)]
    table.extend(map(parse_row, rows))

    longest_per_column = [max(table, key=lambda x: len(x[col]))[col] for col in range(L)]
    widths = list(map(len, longest_per_column))
    styles = [f'{{:{"^" if "center" in styles[i] else ""}{widths[i]}}}' for i in range(L)]
    ret = f'\n**{caption}**```'
    spacing = min(60 - sum(widths), 4)
    ret += '\n' + (' ' * spacing).join(styles[i].format(table[0][i]) for i in range(L))
    ret += '\n' + ('-' * (sum(widths) + spacing * (L - 1)))
    for row in table[1:]:
        ret += '\n' + (' ' * spacing).join(styles[i].format(row[i]) for i in range(L))
    ret = ret.rstrip() + '```'
    return ret


def parse_row(row: list) -> list:
    return list(map(parse_row_entry, row))


def parse_row_entry(entry) -> str:
    if isinstance(entry, str):
        return remove_fields(entry)
    elif isinstance(entry, dict):
        if entry['type'] == 'cell':
            return parse_cell(entry)
        # TODO
    else:
        raise ValueError(f'Unrecognized table.row arguments {list(entry.keys())}')


def parse_cell(cell: dict) -> str:
    if 'roll' in cell:
        return parse_roll(cell['roll'])
    else:
        raise ValueError(f'Unrecognized table.row.cell arguments {list(cell.keys())}')


def parse_roll(roll: dict) -> str:
    if 'exact' in roll:
        return str(roll['exact'])
    elif 'min' in roll and 'max' in roll:
        a, b = str(roll['min']), str(roll['max'])
        if 'pad' in roll:
            N = max(2, max(len(a), len(b)))
            a = '0'*(N-len(a)) + a
            b = '0'*(N-len(b)) + b
        return f'{a}-{b}'
    else:
        raise ValueError(f'Unrecognized table.row.cell.roll arguments {list(roll.keys())}')


class TestTable(unittest.TestCase):
    def test_chaos_bolt(self):
        entry = {
          "type": "table",
          "caption": "Chaos Bolt",
          "colLabels": [
            "{@dice d8}",
            "Damage Type"
          ],
          "colStyles": [
            "col-1 text-center",
            "col-11"
          ],
          "rows": [
            [
              {
                "type": "cell",
                "roll": {
                  "exact": 1
                }
              },
              "Acid"
            ],
            [
              {
                "type": "cell",
                "roll": {
                  "exact": 2
                }
              },
              "Cold"
            ],
            [
              {
                "type": "cell",
                "roll": {
                  "exact": 3
                }
              },
              "Fire"
            ],
            [
              {
                "type": "cell",
                "roll": {
                  "exact": 4
                }
              },
              "Force"
            ],
            [
              {
                "type": "cell",
                "roll": {
                  "exact": 5
                }
              },
              "Lightning"
            ],
            [
              {
                "type": "cell",
                "roll": {
                  "exact": 6
                }
              },
              "Poison"
            ],
            [
              {
                "type": "cell",
                "roll": {
                  "exact": 7
                }
              },
              "Psychic"
            ],
            [
              {
                "type": "cell",
                "roll": {
                  "exact": 8
                }
              },
              "Thunder"
            ]
          ]
        }
        self.assertEqual(format_table(entry),
"""
**Chaos Bolt**```
d8    Damage Type
-----------------
1     Acid       
2     Cold       
3     Fire       
4     Force      
5     Lightning  
6     Poison     
7     Psychic    
8     Thunder```""")


if __name__ == '__main__':
    unittest.main()
