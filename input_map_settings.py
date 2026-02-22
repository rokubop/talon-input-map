"""
User-configurable settings for talon-input-map.
"""
from talon import Module

mod = Module()

mod.setting(
    "input_map_combo_window",
    type=int,
    default=300,
    desc="The time window (ms) to wait for a combo to complete",
)
mod.setting(
    "input_map_edge_debounce_ms",
    type=int,
    default=0,
    desc="Debounce ms for edge-triggered region transitions. 0 = off.",
)
