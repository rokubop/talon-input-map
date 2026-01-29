from talon import Module, actions
from .input_map import (
    input_map_mode_cycle,
    input_map_mode_get,
    input_map_mode_set,
    input_map_handle,
    input_map_event_register,
    input_map_event_unregister,
)
from .input_map_tests import run_tests

mod = Module()

@mod.action_class
class Actions:
    def input_map_handle(name: str):
        """
        Input sources should call this in order to use current `input_map`

        Example:
        ```talon
        parrot(pop):        user.input_map_handle("pop")
        parrot(hiss):       user.input_map_handle("hiss")
        parrot(hiss:stop):  user.input_map_handle("hiss_stop")
        ```

        Or with other input sources:
        ```talon
        key(f13):           user.input_map_handle("pedal_1")
        key(f14):           user.input_map_handle("pedal_2")
        ```
        """
        input_map_handle(name)

    def input_map_handle_parrot(name: str, power: float, f0: float, f1: float, f2: float):
        """
        If you want to filter based on additional parameters from parrot,
        you can use this instead of `input_map_handle`.

        Example:
        ```talon
        parrot(pop):        user.input_map_handle_parrot("pop", power, f0, f1, f2)
        parrot(hiss):       user.input_map_handle_parrot("hiss", power, f0, f1, f2)
        parrot(hiss:stop):  user.input_map_handle_parrot("hiss_stop", power, f0, f1, f2)
        ```
        """
        input_map_handle(name, power=power, f0=f0, f1=f1, f2=f2)

    def input_map_handle_xy(name: str, x: float, y: float):
        """
        If you want to filter based on additional parameters from gaze XY,
        you can use this instead of `input_map_handle`.

        Example:
        ```talon
        face(gaze_xy):     user.input_map_handle_xy("gaze_xy", x, y)
        ```
        """
        input_map_handle(name, x=x, y=y)

    def input_map_handle_value(name: str, value: bool):
        """
        For inputs that have a value like face change

        Example:
        ```talon
        face(dimple_left:change):   user.input_map_handle_value("dimple_left", value)
        ```
        """
        input_map_handle(name, value=value)


    def input_map():
        """
        Define your input map in a ctx here.

        Example:
        ```py
        input_map = {
            "pop":       ("pop", lambda: actions.mouse_click(0)),
            "hiss":      ("hiss", lambda: actions.scroll(1)),
            "hiss_stop": ("hiss", lambda: actions.scroll(-1)),
        }

        # or
        input_map = {
            "default": {
                "pop":       ("pop", lambda: actions.mouse_click(0)),
                "hiss":      ("hiss", lambda: actions.scroll(1)),
                ...
            },
            "other_mode": {
                "pop":       ("pop", lambda: actions.mouse_click(0)),
                "hiss":      ("hiss", lambda: actions.scroll(1)),
                ...
            },

        @ctx.action_class("user")
        class user_actions:
            def input_map():
                return input_map
        ```

        Options:
        ```py
        "input"         - default
        "input input"   - combo results in action
        "input:th_100"  - throttle of 100ms (triggered once every 100ms)
        "input:th"      - default throttle
        "input:db_100"  - debounce of 100ms (triggered after 100ms of continuous input)
        "input:db"      - default debounce
        "tut $input"    - variable pattern passed to lambda as argument
        ```
        """
        return {}

    def input_map_mode_set(mode: str):
        """
        Change the current mode. Only applicable for input maps that define
        "default" and other modes.

        Example:
        ```py
        input_map = {
            "default": input_map_default,
            "other": {
                **input_map_default,
                **input_map_other,
            }
        }

        actions.user.input_map_mode("other")
        ```
        """
        input_map_mode_set(mode)

    def input_map_mode_cycle() -> str:
        """
        Cycle to the next mode. Only works if you have defined
        multiple modes in your `input_map`. Also returns the
        string value of the next mode.

        ```
        input_map = {
            "default": input_map_default,
            "other": {
                **input_map_default,
                **input_map_other,
            }
        }
        ```
        """
        return input_map_mode_cycle()

    def input_map_mode_get() -> str:
        """
        Get the current mode
        """
        return input_map_mode_get()

    def input_map_format_display(
        input_map: dict[str, tuple[str, callable]],
    ) -> tuple[list[str], list[str]]:
        """
        Format/prettify into commands/actions
        ```
        (cmds, acts) = input_map_format_display(input_map)
        ```
        """
        cmds, acts = [], []

        for command, action_tuple in input_map.items():
            if isinstance(action_tuple, tuple):
                if len(action_tuple) == 0:
                    continue
                action = action_tuple[0]
            else:
                action = action_tuple

            if action == "":
                continue
            command = command.split(":")[0]
            cmds.append(command)
            acts.append(action)

        return (cmds, acts)

    def input_map_format_display_dict(
        input_map: dict[str, tuple[str, callable]] = None,
        mode: str = None,
    ) -> dict[str, callable]:
        """
        Format/prettify into dictionary of commands/action names
        ```
        display_dict = input_map_format_display(input_map)
        ```
        """
        if not input_map:
            input_map = actions.user.input_map()
        if "default" in input_map:
            if mode is None:
                mode = actions.user.input_map_mode_get()
            input_map = input_map.get(mode, input_map["default"])
        display_dict = {}

        for command, action_tuple in input_map.items():
            if isinstance(action_tuple, tuple):
                if len(action_tuple) == 0:
                    continue
                action = action_tuple[0]
            else:
                action = action_tuple

            if action == "":
                continue
            command = command.split(":")[0]
            display_dict[command] = action

        return display_dict

    def input_map_event_register(on_input: callable):
        """
        Register input event triggered from input_map
        ```py
        def on_input(input: str, command: str):
            print(input, command)
        actions.user.input_map_event_register(on_input)
        ```
        """
        input_map_event_register(on_input)

    def input_map_event_unregister(on_input: callable):
        """
        Unregister event set by actions.user.input_map_event_register
        """
        input_map_event_unregister(on_input)

    def input_map_tests():
        """
        Run this directly in talon REPL: `actions.user.input_map_tests()`
        """
        run_tests()
