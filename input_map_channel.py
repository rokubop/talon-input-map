"""
Channel-based InputMap API for explicitly registered input maps.

Unlike the context-based input_map(), channels are registered by name and
can be managed independently of Talon contexts. Multiple channels can be
active simultaneously, each processing inputs independently.
"""
from talon import actions
from .input_map import InputMap

# Registry of channel name -> InputMap instance
_channels: dict[str, InputMap] = {}

# Per-channel event callbacks
_channel_callbacks: dict[str, list[callable]] = {}


def channel_register(channel: str, input_map: dict):
    """Register an input map under a channel name."""
    if channel in _channels:
        print(f"input_map_channel: '{channel}' already registered, keeping existing")
        return
    _channel_callbacks[channel] = []
    # Create event trigger that uses per-channel callbacks
    def event_trigger(event: dict):
        channel_event_trigger(channel, event)
    instance = InputMap(input_map, event_trigger=event_trigger)
    _channels[channel] = instance


def channel_unregister(channel: str):
    """Remove a channel from the registry."""
    if channel in _channels:
        del _channels[channel]
    if channel in _channel_callbacks:
        del _channel_callbacks[channel]


def channel_list() -> list[str]:
    """Return list of registered channel names."""
    return list(_channels.keys())


def channel_get(channel: str, mode: str = None) -> dict:
    """Get input map dict for a channel/mode."""
    if channel not in _channels:
        raise ValueError(f"Channel '{channel}' not registered")
    instance = _channels[channel]
    input_map = instance.input_map_user_ref
    if mode:
        if mode in input_map:
            return input_map[mode]
        raise ValueError(f"Mode '{mode}' not found in channel '{channel}'")
    return input_map


def channel_handle(
    channel: str,
    input_name: str,
    power: float = None,
    f0: float = None,
    f1: float = None,
    f2: float = None,
    x: float = None,
    y: float = None,
    value: float = None
):
    """Execute input handling for a specific channel."""
    if channel not in _channels:
        raise ValueError(f"Channel '{channel}' not registered")
    instance = _channels[channel]
    instance.execute(input_name, power=power, f0=f0, f1=f1, f2=f2, x=x, y=y, value=value)


def channel_mode_set(channel: str, mode: str):
    """Set the mode for a specific channel."""
    if channel not in _channels:
        raise ValueError(f"Channel '{channel}' not registered")
    instance = _channels[channel]
    if mode in instance.input_map_user_ref:
        instance.setup_mode(mode)
    else:
        raise ValueError(f"Mode '{mode}' not found in channel '{channel}'")


def channel_mode_get(channel: str) -> str:
    """Get the current mode for a specific channel."""
    if channel not in _channels:
        raise ValueError(f"Channel '{channel}' not registered")
    return _channels[channel].current_mode


def channel_mode_revert(channel: str) -> str:
    """Revert to the previous mode for a specific channel."""
    if channel not in _channels:
        raise ValueError(f"Channel '{channel}' not registered")
    instance = _channels[channel]
    if instance.previous_mode is not None:
        instance.setup_mode(instance.previous_mode)
    return instance.current_mode


def channel_mode_cycle(channel: str) -> str:
    """Cycle to the next mode for a specific channel."""
    if channel not in _channels:
        raise ValueError(f"Channel '{channel}' not registered")
    instance = _channels[channel]
    modes = list(instance.input_map_user_ref.keys())
    current_mode = instance.current_mode
    if current_mode in modes:
        current_index = modes.index(current_mode)
        next_index = (current_index + 1) % len(modes)
        next_mode = modes[next_index]
        instance.setup_mode(next_mode)
        return next_mode
    else:
        raise ValueError(f"Mode '{current_mode}' not found in channel '{channel}'")


def channel_get_legend(channel: str, mode: str = None) -> dict[str, str]:
    """Get the legend for a channel's input map."""
    if channel not in _channels:
        raise ValueError(f"Channel '{channel}' not registered")
    instance = _channels[channel]
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


def channel_event_register(channel: str, on_input: callable):
    """Register an event callback for a specific channel."""
    if channel not in _channels:
        raise ValueError(f"Channel '{channel}' not registered")
    if channel not in _channel_callbacks:
        _channel_callbacks[channel] = []
    _channel_callbacks[channel].append(on_input)


def channel_event_unregister(channel: str, on_input: callable):
    """Unregister an event callback for a specific channel."""
    if channel not in _channel_callbacks:
        return
    try:
        _channel_callbacks[channel].remove(on_input)
    except ValueError:
        # Try to find by name if reference was lost
        for subscriber in _channel_callbacks[channel]:
            if subscriber.__name__ == on_input.__name__:
                _channel_callbacks[channel].remove(subscriber)
                break


def channel_event_trigger(channel: str, event: dict):
    """Trigger event callbacks for a specific channel."""
    if channel not in _channel_callbacks:
        return
    for callback in _channel_callbacks[channel]:
        callback(event)
