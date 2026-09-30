"""Small S-expression helpers shared by the KiCad project generators."""

from pathlib import Path
import copy
import json
import re

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def q(value):
    return json.dumps(str(value), ensure_ascii=False)


class Atom(str):
    pass


def parse(source):
    tokens = re.findall(r'"(?:\\.|[^"\\])*"|[^\s()]+|[()]', source)
    stack = []
    result = None
    for token in tokens:
        if token == '(':
            item = []
            if stack:
                stack[-1].append(item)
            stack.append(item)
        elif token == ')':
            result = stack.pop()
        else:
            stack[-1].append(json.loads(token) if token.startswith('"') else Atom(token))
    return result


def dump(value):
    if isinstance(value, list):
        return '(' + ' '.join(dump(item) for item in value) + ')'
    if isinstance(value, Atom):
        return str(value)
    return q(value)


def kids(value, key):
    return [item for item in value if isinstance(item, list) and item[0] == key]


def get(value, key):
    return next((item for item in value if isinstance(item, list) and item[0] == key), None)


_cache = {}


def resolve(library, name):
    if library not in _cache:
        if library == 'ESP32C3_SuperMini':
            path = REPOSITORY_ROOT / 'shared/ESP32C3_SuperMini.kicad_sym'
        else:
            path = Path('/usr/share/kicad/symbols') / f'{library}.kicad_sym'
        _cache[library] = {
            item[1]: item for item in kids(parse(path.read_text()), 'symbol')
        }
    symbol = copy.deepcopy(_cache[library][name])
    extends = get(symbol, 'extends')
    if extends:
        base = resolve(library, extends[1])
        symbol.remove(extends)
        for item in base[2:]:
            if not isinstance(item, list):
                continue
            if item[0] == 'property' and any(
                existing[1] == item[1] for existing in kids(symbol, 'property')
            ):
                continue
            if item[0] != 'property' and get(symbol, item[0]) is not None and item[0] != 'symbol':
                continue
            if item[0] == 'symbol':
                item[1] = item[1].replace(base[1] + '_', name + '_')
            symbol.append(item)
    return symbol
