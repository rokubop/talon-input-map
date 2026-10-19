"""user.input_map_types(): the named sets of values input_map takes,
each value described. A param that takes one says so in its docstring:
`Type: input_map.event_type`.

Built in input_map_parse from the tables the parser runs on, so there is
no list to keep in step.
"""

from talon import Module

from .input_map_parse import types

mod = Module()


@mod.action_class
class Actions:
    def input_map_types() -> dict:
        """Named sets of values input_map takes, each value described:
        {name: {"desc": str, "values": [{"id": str, "desc": str, ...}]}}.
        A value can carry more, as a segment's pattern and default."""
        return types()
