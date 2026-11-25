"""
Channel-based InputMap API for explicitly registered input maps.

Unlike the context-based input_map(), channels are registered by name and
can be managed independently of Talon contexts. Multiple channels can be
active simultaneously, each processing inputs independently.

The registry and each channel's state are read and changed under input-map's
lock (`state_lock`). Listeners hear a mode change once it's let go.
"""
from talon import actions
from .input_map import InputMap, InputMapEvent
from .input_map_parse import build_legend, mode_entries, state_lock, locked, fire

# Registry of channel name -> InputMap instance
_channels: dict[str, InputMap] = {}

# Per-channel event callbacks, kept apart from the channels: a listener
# can subscribe before its channel exists, and outlives it.
_channel_callbacks: dict[str, list[callable]] = {}


def _instance(channel: str) -> InputMap:
    """Under the lock"""
    if channel not in _channels:
        raise ValueError(f"Channel '{channel}' not registered")
    return _channels[channel]


def channel_register(channel: str, input_map: dict):
    """Register an input map under a channel name."""
    with state_lock:
        if channel in _channels:
            print(f"input_map_channel: '{channel}' already registered, keeping existing")
            return
        # Create event trigger that uses per-channel callbacks
        def event_trigger(event: dict):
            channel_event_trigger(channel, event)
        instance = InputMap(input_map, event_trigger=event_trigger)
        _channels[channel] = instance


def channel_unregister(channel: str):
    """Remove a channel from the registry. Its event callbacks stay."""
    with state_lock:
        _channels.pop(channel, None)


def channel_list() -> list[str]:
    """Return list of registered channel names."""
    with state_lock:
        return list(_channels.keys())


def channel_get(channel: str, mode: str = None) -> dict:
    """Get input map dict for a channel/mode."""
    with state_lock:
        input_map = _instance(channel).input_map_user_ref
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
    """Execute input handling for a specific channel, as an "input" job"""
    with state_lock:
        instance = _instance(channel)
    instance.execute(input_name, power=power, f0=f0, f1=f1, f2=f2, x=x, y=y, value=value)


def _mode_changed(channel: str, mode: str):
    """Listeners hear it once the lock is let go"""
    fire(lambda: channel_event_trigger(channel, InputMapEvent(
        type="mode_change",
        mode=mode,
    )))


def channel_mode_set(channel: str, mode: str):
    """Set the mode for a specific channel."""
    def mode_set():
        instance = _instance(channel)
        if mode not in instance.input_map_user_ref:
            raise ValueError(f"Mode '{mode}' not found in channel '{channel}'")
        instance.setup_mode(mode)
        _mode_changed(channel, mode)
    locked(mode_set)


def channel_mode_get(channel: str) -> str:
    """Get the current mode for a specific channel."""
    with state_lock:
        return _instance(channel).current_mode


def channel_mode_revert(channel: str) -> str:
    """Revert to the previous mode for a specific channel."""
    def revert():
        instance = _instance(channel)
        if instance.previous_mode is not None:
            instance.setup_mode(instance.previous_mode)
            _mode_changed(channel, instance.current_mode)
        return instance.current_mode
    return locked(revert)


def channel_mode_cycle(channel: str) -> str:
    """Cycle to the next mode for a specific channel."""
    def cycle():
        instance = _instance(channel)
        modes = list(instance.input_map_user_ref.keys())
        current_mode = instance.current_mode
        if current_mode not in modes:
            raise ValueError(f"Mode '{current_mode}' not found in channel '{channel}'")
        next_mode = modes[(modes.index(current_mode) + 1) % len(modes)]
        instance.setup_mode(next_mode)
        _mode_changed(channel, next_mode)
        return next_mode
    return locked(cycle)


def channel_get_legend(channel: str, mode: str = None) -> dict[str, str]:
    """Get the legend for a channel's input map."""
    with state_lock:
        instance = _instance(channel)
    return build_legend(mode_entries(instance.input_map_user_ref, mode,
                                     lambda: instance.current_mode))


def channel_event_register(channel: str, on_input: callable):
    """Register an event callback for a channel, registered yet or not."""
    with state_lock:
        if channel not in _channels and channel not in _channel_callbacks:
            known = ", ".join(sorted(_channels)) or "none"
            print(f"input_map_channel: listening on '{channel}', which isn't registered yet "
                  f"(registered: {known})")
        _channel_callbacks.setdefault(channel, []).append(on_input)


def channel_event_unregister(channel: str, on_input: callable):
    """Unregister an event callback for a specific channel."""
    with state_lock:
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


def channel_event_trigger(channel: str, event: InputMapEvent):
    """Trigger event callbacks for a specific channel."""
    with state_lock:
        callbacks = list(_channel_callbacks.get(channel, ()))
    for callback in callbacks:
        callback(event)
