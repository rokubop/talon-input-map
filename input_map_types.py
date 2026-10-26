"""Value sets for user.input_map_types(), built from the tables the parser runs on."""

from talon import Module

from .input_map import EVENT_TYPES
from .input_map_parse import MODIFIERS, CONDITION_VARIABLES, OPERATORS, RELEASE_SUFFIXES

mod = Module()


def _values(table: dict) -> list:
    out = []
    for name, v in table.items():
        out.append({"id": name, **v} if isinstance(v, dict) else {"id": name, "desc": v})
    return out


def types() -> dict:
    return {
        "modifier": {
            "desc": "A ':' part of a key, as in 'pop:power>10:th_90'. In pattern, group 1 is the number; a condition's groups are variable, operator, number. A bare one uses default or default_setting.",
            "values": _values(MODIFIERS),
        },
        "condition_variable": {
            "desc": "What a condition compares. source is the handle action that provides it.",
            "values": _values(CONDITION_VARIABLES),
        },
        "operator": {
            "desc": "How a condition compares its variable with its number.",
            "values": _values(OPERATORS),
        },
        "release_suffix": {
            "desc": "Ends an input's name to make it the release.",
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
        """Named sets of values input_map takes:
        {name: {"desc": str, "values": [{"id": str, "desc": str, ...}]}}.
        A value can carry more, like a modifier's pattern and default."""
        return types()
