"""
Lightweight single-input InputMap API.

Unlike the full input_map (context-based) or channels (explicitly registered),
input_map_single provides a minimal way to make a single input mode-aware.
Auto-registers on first call; re-registers if the map reference changes.
"""
from .input_map import InputMap, input_map_event_trigger

# Registry of name -> InputMap instance
_singles: dict[str, InputMap] = {}
# Track the user's map reference for auto-re-registration
_singles_map_ref: dict[str, dict] = {}
# Track mode order per name for cycling
_singles_mode_order: dict[str, list] = {}


def normalize_single_map(name: str, user_map: dict) -> dict:
    """Convert user-friendly single map format to InputMap-compatible mode dict.

    Supported formats:
      - Simple:   {"click": lambda: ..., "repeat": lambda: ...}
      - Tuple:    {"click": ("left click", lambda: ...), ...}
      - Expanded: {"click": {"pop": ("click", lambda: ...), ...}, ...}
    """
    first_value = next(iter(user_map.values()))

    if callable(first_value):
        # Simple: wrap each callable as (name, {name: ("", callable)})
        return {mode: {name: ("", action)} for mode, action in user_map.items()}
    elif isinstance(first_value, tuple):
        # Tuple: wrap each tuple as {name: tuple}
        return {mode: {name: action_tuple} for mode, action_tuple in user_map.items()}
    elif isinstance(first_value, dict):
        # Expanded: pass through as-is
        return user_map
    else:
        raise ValueError(f"input_map_single '{name}': unsupported map value type: {type(first_value)}")


def _register_single(name: str, user_map: dict):
    """Create and register an InputMap instance for a single input."""
    normalized = normalize_single_map(name, user_map)
    modes = list(normalized.keys())
    first_mode = modes[0]

    def event_trigger(ctx):
        ctx["single"] = name
        input_map_event_trigger(ctx)

    instance = InputMap(event_trigger=event_trigger)
    instance.input_map_user_ref = normalized
    instance._mode_cache = {}
    instance.setup_mode(first_mode)

    _singles[name] = instance
    _singles_map_ref[name] = user_map
    _singles_mode_order[name] = modes


def single_handle(
    name: str,
    user_map: dict,
    power: float = None,
    f0: float = None,
    f1: float = None,
    f2: float = None,
    x: float = None,
    y: float = None,
    value: float = None
):
    """Main entry point for single input handling."""
    if name not in _singles or _singles_map_ref[name] is not user_map:
        _register_single(name, user_map)

    _singles[name].execute(name, power=power, f0=f0, f1=f1, f2=f2, x=x, y=y, value=value)


def single_mode_set(name: str, mode: str):
    """Set the mode for a single input."""
    if name not in _singles:
        raise ValueError(f"Single '{name}' not registered")
    instance = _singles[name]
    if mode in instance.input_map_user_ref:
        instance.setup_mode(mode)
    else:
        raise ValueError(f"Mode '{mode}' not found in single '{name}'")


def single_mode_get(name: str) -> str:
    """Get the current mode for a single input."""
    if name not in _singles:
        raise ValueError(f"Single '{name}' not registered")
    return _singles[name].current_mode


def single_mode_cycle(name: str) -> str:
    """Cycle to the next mode for a single input."""
    if name not in _singles:
        raise ValueError(f"Single '{name}' not registered")
    instance = _singles[name]
    modes = _singles_mode_order[name]
    current_mode = instance.current_mode
    if current_mode in modes:
        current_index = modes.index(current_mode)
        next_index = (current_index + 1) % len(modes)
        next_mode = modes[next_index]
        instance.setup_mode(next_mode)
        return next_mode
    else:
        raise ValueError(f"Mode '{current_mode}' not found in single '{name}'")


def single_mode_revert(name: str) -> str:
    """Revert to the previous mode for a single input."""
    if name not in _singles:
        raise ValueError(f"Single '{name}' not registered")
    instance = _singles[name]
    if instance.previous_mode is not None:
        instance.setup_mode(instance.previous_mode)
    return instance.current_mode


def single_get_legend(name: str, user_map: dict, mode: str = None) -> dict[str, str]:
    """Get the legend for a single input map.

    Returns {input: label} with modifiers stripped and empty entries filtered.
    """
    if name not in _singles or _singles_map_ref[name] is not user_map:
        _register_single(name, user_map)

    instance = _singles[name]
    normalized = instance.input_map_user_ref

    if mode is None:
        mode = instance.current_mode

    if mode not in normalized:
        raise ValueError(f"Mode '{mode}' not found in single '{name}'")

    commands = normalized[mode]
    legend = {}
    for input_key, action_tuple in commands.items():
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
