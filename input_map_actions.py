from talon import Module, actions
from .input_map import (
    input_map_mode_cycle,
    input_map_mode_get,
    input_map_mode_set,
    input_map_mode_revert,
    input_map_handle,
    input_map_event_register,
    input_map_event_unregister,
    input_map_get,
)
from .input_map_profile import (
    profile_register,
    profile_unregister,
    profile_list,
    profile_get,
    profile_handle,
    profile_mode_set,
    profile_mode_get,
    profile_mode_cycle,
    profile_mode_revert,
    profile_get_legend,
    profile_event_register,
    profile_event_unregister,
)
from .input_map_single import (
    single_handle,
    single_mode_set,
    single_mode_get,
    single_mode_cycle,
    single_mode_revert,
    single_get_legend,
)
from .input_map_tests import run_tests

mod = Module()

@mod.action_class
class Actions:
    def input_map_handle(name: str):
        """
        Handle a basic input with no extra data.

        Example:
        ```talon
        parrot(pop):        user.input_map_handle("pop")
        parrot(hiss):       user.input_map_handle("hiss")
        parrot(hiss:stop):  user.input_map_handle("hiss_stop")
        key(f13):           user.input_map_handle("pedal_1")
        ```
        """
        input_map_handle(name)

    def input_map_handle_parrot(name: str, power: float, f0: float, f1: float, f2: float):
        """
        Handle a parrot input with frequency data.

        Example:
        ```talon
        parrot(pop):        user.input_map_handle_parrot("pop", power, f0, f1, f2)
        ```
        """
        input_map_handle(name, power=power, f0=f0, f1=f1, f2=f2)

    def input_map_handle_xy(name: str, x: float, y: float):
        """
        Handle an xy input (gaze, gamepad stick).

        Example:
        ```talon
        face(gaze_xy):           user.input_map_handle_xy("gaze", gaze_x, gaze_y)
        gamepad(left_xy:repeat): user.input_map_handle_xy("left_stick", left_x, left_y)
        ```
        """
        input_map_handle(name, x=x, y=y)

    def input_map_handle_value(name: str, value: float):
        """
        Handle a value change input (face feature, gamepad trigger).

        Example:
        ```talon
        face(dimple_left:change): user.input_map_handle_value("dimple_left", value)
        gamepad(l2:change):       user.input_map_handle_value("l2", value)
        ```
        """
        input_map_handle(name, value=value)

    def input_map_handle_bool(name: str, active: bool):
        """
        Handle a boolean input (active/stop).

        Maps active=True to "name" and active=False to "name_stop".

        Example:
        ```py
        noise.register("hiss", lambda active: actions.user.input_map_handle_bool("hiss", active))
        ```
        """
        input_map_handle(name if active else f"{name}_stop")

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
        "input:power>10"        - conditional on power value
        "input:x<500:y<500"     - multiple conditions (AND)
        "input:power>10:th_100" - conditional with throttle
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

    def input_map_mode_revert() -> str:
        """
        Revert to the previous mode.

        Example:
        ```py
        actions.user.input_map_mode_set("combat")
        actions.user.input_map_mode_revert()  # back to previous mode
        ```
        """
        return input_map_mode_revert()

    def input_map_get_legend(
        input_map: dict[str, tuple[str, callable]] = None,
        mode: str = None,
    ) -> dict[str, str]:
        """
        Get the legend for an input map.

        Returns {input: label} with modifiers stripped and empty entries filtered.

        - If input_map not provided, uses current active input_map
        - If mode specified, uses that mode
        """
        if not input_map:
            input_map = actions.user.input_map()
        if "default" in input_map:
            if mode is None:
                mode = actions.user.input_map_mode_get()
            input_map = input_map.get(mode, input_map["default"])

        legend = {}
        for input_key, action_tuple in input_map.items():
            if isinstance(action_tuple, tuple):
                if len(action_tuple) == 0:
                    continue
                label = action_tuple[0]
            else:
                label = action_tuple

            if label == "":
                continue
            input_key = input_key.split(":")[0]
            legend[input_key] = label

        return legend

    def input_map_event_register(on_input: callable):
        """
        Register input event triggered from input_map
        ```py
        def on_input(event: dict):
            print(event["input"], event["label"])
        actions.user.input_map_event_register(on_input)
        ```
        """
        input_map_event_register(on_input)

    def input_map_event_unregister(on_input: callable):
        """
        Unregister event set by actions.user.input_map_event_register
        """
        input_map_event_unregister(on_input)

    def input_map_get(mode: str = None) -> dict:
        """
        Get the input map dict for the current or specified mode.

        Example:
        ```py
        current_map = actions.user.input_map_get()
        specific_mode_map = actions.user.input_map_get("combat")
        ```
        """
        return input_map_get(mode)

    # Profile-based input map actions

    def input_map_profile_register(profile: str, input_map: dict):
        """
        Register an input map under a profile name.

        Example:
        ```py
        my_input_map = {
            "pop": ("click", lambda: actions.mouse_click(0)),
        }
        actions.user.input_map_profile_register("my_profile", my_input_map)
        ```
        """
        profile_register(profile, input_map)

    def input_map_profile_unregister(profile: str):
        """
        Remove a profile from the registry.
        """
        profile_unregister(profile)

    def input_map_profile_list() -> list[str]:
        """
        Return list of registered profile names.
        """
        return profile_list()

    def input_map_profile_get(profile: str, mode: str = None) -> dict:
        """
        Get input map dict for a profile/mode.
        """
        return profile_get(profile, mode)

    def input_map_profile_handle(profile: str, input_name: str):
        """
        Handle a basic input for a specific profile.

        Example:
        ```talon
        parrot(pop): user.input_map_profile_handle("my_profile", "pop")
        ```
        """
        profile_handle(profile, input_name)

    def input_map_profile_handle_parrot(profile: str, input_name: str, power: float, f0: float, f1: float, f2: float):
        """
        Handle a parrot input with frequency data for a specific profile.

        Example:
        ```talon
        parrot(pop): user.input_map_profile_handle_parrot("my_profile", "pop", power, f0, f1, f2)
        ```
        """
        profile_handle(profile, input_name, power=power, f0=f0, f1=f1, f2=f2)

    def input_map_profile_handle_xy(profile: str, input_name: str, x: float, y: float):
        """
        Handle an xy input for a specific profile.

        Example:
        ```talon
        face(gaze_xy): user.input_map_profile_handle_xy("my_profile", "gaze", gaze_x, gaze_y)
        ```
        """
        profile_handle(profile, input_name, x=x, y=y)

    def input_map_profile_handle_value(profile: str, input_name: str, value: float):
        """
        Handle a value change input for a specific profile.

        Example:
        ```talon
        face(dimple_left:change): user.input_map_profile_handle_value("my_profile", "dimple_left", value)
        ```
        """
        profile_handle(profile, input_name, value=value)

    def input_map_profile_handle_bool(profile: str, input_name: str, active: bool):
        """
        Handle a boolean input for a specific profile.

        Maps active=True to "name" and active=False to "name_stop".

        Example:
        ```py
        noise.register("hiss", lambda active: actions.user.input_map_profile_handle_bool("my_profile", "hiss", active))
        ```
        """
        profile_handle(profile, input_name if active else f"{input_name}_stop")

    def input_map_profile_mode_set(profile: str, mode: str):
        """
        Set the mode for a specific profile.
        """
        profile_mode_set(profile, mode)

    def input_map_profile_mode_get(profile: str) -> str:
        """
        Get the current mode for a specific profile.
        """
        return profile_mode_get(profile)

    def input_map_profile_mode_cycle(profile: str) -> str:
        """
        Cycle to the next mode for a specific profile.
        """
        return profile_mode_cycle(profile)

    def input_map_profile_mode_revert(profile: str) -> str:
        """
        Revert to the previous mode for a specific profile.

        Example:
        ```py
        actions.user.input_map_profile_mode_set("my_profile", "combat")
        actions.user.input_map_profile_mode_revert("my_profile")  # back to previous
        ```
        """
        return profile_mode_revert(profile)

    def input_map_profile_get_legend(profile: str, mode: str = None) -> dict[str, str]:
        """
        Get the legend for a profile's input map.

        Returns {input: label} with modifiers stripped and empty entries filtered.
        """
        return profile_get_legend(profile, mode)

    def input_map_profile_event_register(profile: str, on_input: callable):
        """
        Register an event callback for a specific profile.

        Example:
        ```py
        def on_input(event: dict):
            print(f"Profile input: {event['input']} -> {event['label']}")
        actions.user.input_map_profile_event_register("my_profile", on_input)
        ```
        """
        profile_event_register(profile, on_input)

    def input_map_profile_event_unregister(profile: str, on_input: callable):
        """
        Unregister an event callback for a specific profile.
        """
        profile_event_unregister(profile, on_input)

    # Single input map actions

    def input_map_single(name: str, map: dict):
        """
        Handle a basic single input.

        Example:
        ```talon
        noise(pop): user.input_map_single("pop", pop_map)
        ```
        """
        single_handle(name, map)

    def input_map_single_parrot(name: str, map: dict, power: float, f0: float, f1: float, f2: float):
        """
        Handle a parrot single input with frequency data.

        Example:
        ```talon
        parrot(pop): user.input_map_single_parrot("pop", pop_map, power, f0, f1, f2)
        ```
        """
        single_handle(name, map, power=power, f0=f0, f1=f1, f2=f2)

    def input_map_single_xy(name: str, map: dict, x: float, y: float):
        """
        Handle an xy single input.

        Example:
        ```talon
        face(gaze_xy): user.input_map_single_xy("gaze", gaze_map, gaze_x, gaze_y)
        ```
        """
        single_handle(name, map, x=x, y=y)

    def input_map_single_value(name: str, map: dict, value: float):
        """
        Handle a value change single input.

        Example:
        ```talon
        face(dimple_left:change): user.input_map_single_value("dimple", dimple_map, value)
        ```
        """
        single_handle(name, map, value=value)

    def input_map_single_bool(name: str, map: dict, active: bool):
        """
        Handle a boolean single input.

        Maps active=True to "name" and active=False to "name_stop".

        Example:
        ```py
        noise.register("hiss", lambda active: actions.user.input_map_single_bool("hiss", hiss_map, active))
        ```
        """
        single_handle(name if active else f"{name}_stop", map)

    def input_map_single_mode_set(name: str, mode: str):
        """
        Set the mode for a single input.
        """
        single_mode_set(name, mode)

    def input_map_single_mode_get(name: str) -> str:
        """
        Get the current mode for a single input.
        """
        return single_mode_get(name)

    def input_map_single_mode_cycle(name: str) -> str:
        """
        Cycle to the next mode for a single input.
        """
        return single_mode_cycle(name)

    def input_map_single_mode_revert(name: str) -> str:
        """
        Revert to the previous mode for a single input.
        """
        return single_mode_revert(name)

    def input_map_single_get_legend(name: str, map: dict, mode: str = None) -> dict[str, str]:
        """
        Get the legend for a single input map.

        Returns {input: label} with modifiers stripped and empty entries filtered.
        """
        return single_get_legend(name, map, mode)

    def input_map_tests():
        """
        Run this directly in talon REPL: `actions.user.input_map_tests()`
        """
        run_tests()
