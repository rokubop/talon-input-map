"""user.input_map_types(): the named sets of values input_map takes,
each value described. A param that takes one says so in its docstring:
`Type: input_map.event_type`.

Read from the tables the parser runs on, so there is no list to keep in
step.
"""

from talon import Module

from .input_map import EVENT_TYPES
from .input_map_parse import SEGMENTS, CONDITION_VARIABLES, OPERATORS, RELEASE_SUFFIXES

mod = Module()


def _values(table: dict) -> list:
    out = []
    for name, v in table.items():
        out.append({"id": name, **v} if isinstance(v, dict) else {"id": name, "desc": v})
    return out


def types() -> dict:
    return {
        "segment": {
            "desc": "A ':' segment on an input map key, as in 'pop:power>10:th_90'. pattern matches the whole segment, its group 1 being the number when it takes one; a condition's groups are variable, operator, number. A bare one with a default stands for it; default_setting names the setting that holds it instead.",
            "values": _values(SEGMENTS),
        },
        "condition_variable": {
            "desc": "What a condition compares. Each is only there when the input comes in through an action that hands it over: source is which.",
            "values": _values(CONDITION_VARIABLES),
        },
        "operator": {
            "desc": "How a condition compares its variable with its number.",
            "values": _values(OPERATORS),
        },
        "release_suffix": {
            "desc": "The end of an input's name that makes its key the input letting go.",
            "values": _values(RELEASE_SUFFIXES),
        },
        "event_type": {
            "desc": "What an input_map event is about.",
            "values": _values(EVENT_TYPES),
        },
    }


@mod.action_class
class Actions:
    def input_map_types() -> dict:
        """Named sets of values input_map takes, each value described:
        {name: {"desc": str, "values": [{"id": str, "desc": str, ...}]}}.
        A value can carry more, as a segment's pattern and default."""
        return types()
