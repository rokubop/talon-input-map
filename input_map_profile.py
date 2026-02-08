"""
Profile-based InputMap API for explicitly registered input maps.

Unlike the context-based input_map(), profiles are registered by name and
can be managed independently of Talon contexts.
"""
from talon import actions
from .input_map import InputMap

# Registry of profile name -> InputMap instance
_profiles: dict[str, InputMap] = {}

# Per-profile event callbacks
_profile_callbacks: dict[str, list[callable]] = {}


def profile_register(profile: str, input_map: dict):
    """Register an input map under a profile name."""
    if profile in _profiles:
        print(f"input_map_profile: '{profile}' already registered, keeping existing")
        return
    _profile_callbacks[profile] = []
    # Create event trigger that uses per-profile callbacks
    def event_trigger(event: dict):
        profile_event_trigger(profile, event)
    instance = InputMap(input_map, event_trigger=event_trigger)
    _profiles[profile] = instance


def profile_unregister(profile: str):
    """Remove a profile from the registry."""
    if profile in _profiles:
        del _profiles[profile]
    if profile in _profile_callbacks:
        del _profile_callbacks[profile]


def profile_list() -> list[str]:
    """Return list of registered profile names."""
    return list(_profiles.keys())


def profile_get(profile: str, mode: str = None) -> dict:
    """Get input map dict for a profile/mode."""
    if profile not in _profiles:
        raise ValueError(f"Profile '{profile}' not registered")
    instance = _profiles[profile]
    input_map = instance.input_map_user_ref
    if mode:
        if mode in input_map:
            return input_map[mode]
        raise ValueError(f"Mode '{mode}' not found in profile '{profile}'")
    return input_map


def profile_handle(
    profile: str,
    input_name: str,
    power: float = None,
    f0: float = None,
    f1: float = None,
    f2: float = None,
    x: float = None,
    y: float = None,
    value: float = None
):
    """Execute input handling for a specific profile."""
    if profile not in _profiles:
        raise ValueError(f"Profile '{profile}' not registered")
    instance = _profiles[profile]
    instance.execute(input_name, power=power, f0=f0, f1=f1, f2=f2, x=x, y=y, value=value)


def profile_mode_set(profile: str, mode: str):
    """Set the mode for a specific profile."""
    if profile not in _profiles:
        raise ValueError(f"Profile '{profile}' not registered")
    instance = _profiles[profile]
    if mode in instance.input_map_user_ref:
        instance.setup_mode(mode)
    else:
        raise ValueError(f"Mode '{mode}' not found in profile '{profile}'")


def profile_mode_get(profile: str) -> str:
    """Get the current mode for a specific profile."""
    if profile not in _profiles:
        raise ValueError(f"Profile '{profile}' not registered")
    return _profiles[profile].current_mode


def profile_mode_revert(profile: str) -> str:
    """Revert to the previous mode for a specific profile."""
    if profile not in _profiles:
        raise ValueError(f"Profile '{profile}' not registered")
    instance = _profiles[profile]
    if instance.previous_mode is not None:
        instance.setup_mode(instance.previous_mode)
    return instance.current_mode


def profile_mode_cycle(profile: str) -> str:
    """Cycle to the next mode for a specific profile."""
    if profile not in _profiles:
        raise ValueError(f"Profile '{profile}' not registered")
    instance = _profiles[profile]
    modes = list(instance.input_map_user_ref.keys())
    current_mode = instance.current_mode
    if current_mode in modes:
        current_index = modes.index(current_mode)
        next_index = (current_index + 1) % len(modes)
        next_mode = modes[next_index]
        instance.setup_mode(next_mode)
        return next_mode
    else:
        raise ValueError(f"Mode '{current_mode}' not found in profile '{profile}'")


def profile_get_legend(profile: str, mode: str = None) -> dict[str, str]:
    """Get the legend for a profile's input map."""
    if profile not in _profiles:
        raise ValueError(f"Profile '{profile}' not registered")
    instance = _profiles[profile]
    input_map = instance.input_map_user_ref

    if "default" in input_map:
        if mode is None:
            mode = instance.current_mode
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


def profile_event_register(profile: str, on_input: callable):
    """Register an event callback for a specific profile."""
    if profile not in _profiles:
        raise ValueError(f"Profile '{profile}' not registered")
    if profile not in _profile_callbacks:
        _profile_callbacks[profile] = []
    _profile_callbacks[profile].append(on_input)


def profile_event_unregister(profile: str, on_input: callable):
    """Unregister an event callback for a specific profile."""
    if profile not in _profile_callbacks:
        return
    try:
        _profile_callbacks[profile].remove(on_input)
    except ValueError:
        # Try to find by name if reference was lost
        for subscriber in _profile_callbacks[profile]:
            if subscriber.__name__ == on_input.__name__:
                _profile_callbacks[profile].remove(subscriber)
                break


def profile_event_trigger(profile: str, event: dict):
    """Trigger event callbacks for a specific profile."""
    if profile not in _profile_callbacks:
        return
    for callback in _profile_callbacks[profile]:
        callback(event)
