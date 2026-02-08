"""
Core InputMap class and runtime execution logic (hot path).
"""
from talon import Module, actions, cron, settings
from .input_map_parse import (
    categorize_commands,
    match_variable_pattern,
    execute_variable_action,
    evaluate_conditions,
)

mod = Module()

_REGION_ELSE = -1

event_subscribers = []

mod.setting("input_map_combo_window", type=int, default=300, desc="The time window to wait for a combo to complete")

class InputMap():
    def __init__(self, input_map: dict = None, event_trigger: callable = None):
        self.input_map_user_ref = None
        self.current_mode = None
        self.immediate_commands = {}
        self.delayed_commands = {}
        self.immediate_variable_patterns = {}
        self.delayed_variable_patterns = {}
        self.has_variables = False
        self.immediate_conditional = {}
        self.delayed_conditional = {}
        self.has_conditions = False
        self._context = {}
        self._edge_triggered_bases = set()
        self._edge_else_actions = {}
        self._active_region = {}
        self.has_edge_triggered = False
        self.base_pairs = set()
        self.combo_chain = ""
        self.combo_job = None
        self.base_inputs = None
        self.pending_combo = None
        self.combo_window = "300ms"
        self.unique_combos = set()
        self._mode_cache = {}
        self._throttle_busy = {}
        self._debounce_busy = {}
        self._event_trigger = event_trigger
        if input_map is not None:
            self.setup(input_map)

    def _trigger_event(self, input: str, label: str):
        """Trigger event using custom callback if provided, otherwise use global."""
        ctx = self._context
        ctx["input"] = input
        ctx["label"] = label
        ctx["mode"] = self.current_mode
        if self._event_trigger:
            self._event_trigger(ctx)
        else:
            input_map_event_trigger(ctx)

    def setup_mode(self, mode):
        if mode:
            if mode == self.current_mode:
                return
            else:
                input_map = self.input_map_user_ref[mode]
        else:
            input_map = self.input_map_user_ref
        if self.combo_job:
            cron.cancel(self.combo_job)
            self.combo_job = None
        self.current_mode = mode
        self.combo_chain = ""
        self.pending_combo = None

        if mode in self._mode_cache:
            cached = self._mode_cache[mode]
            self.immediate_commands = cached["immediate_commands"]
            self.delayed_commands = cached["delayed_commands"]
            self.immediate_variable_patterns = cached["immediate_variable_patterns"]
            self.delayed_variable_patterns = cached["delayed_variable_patterns"]
            self.has_variables = cached["has_variables"]
            self.immediate_conditional = cached["immediate_conditional"]
            self.delayed_conditional = cached["delayed_conditional"]
            self.has_conditions = cached["has_conditions"]
            self._edge_triggered_bases = cached["edge_triggered_bases"]
            self._edge_else_actions = cached["edge_else_actions"]
            self.has_edge_triggered = cached["has_edge_triggered"]
            self._active_region = {}
            self.base_inputs = cached["base_input_set"]
            self.base_pairs = cached["base_pairs"]
            self.unique_combos = cached["unique_combos"]
            combo_window = settings.get("user.input_map_combo_window", 300)
            self.combo_window = f"{combo_window}ms"
            return

        commands = input_map.get("commands", {}) if "commands" in input_map else input_map

        categorized = categorize_commands(commands, self._throttle_busy, self._debounce_busy, context_ref=self._context)
        self.immediate_commands = categorized["immediate_commands"]
        self.delayed_commands = categorized["delayed_commands"]
        self.immediate_variable_patterns = categorized["immediate_variable_patterns"]
        self.delayed_variable_patterns = categorized["delayed_variable_patterns"]
        self.has_variables = categorized["has_variables"]
        self.immediate_conditional = categorized["immediate_conditional"]
        self.delayed_conditional = categorized["delayed_conditional"]
        self.has_conditions = categorized["has_conditions"]
        self._edge_triggered_bases = categorized["edge_triggered_bases"]
        self._edge_else_actions = categorized["edge_else_actions"]
        self.has_edge_triggered = categorized["has_edge_triggered"]
        self._active_region = {}
        self.base_inputs = categorized["base_input_set"]
        self.base_pairs = categorized["base_pairs"]
        self.unique_combos = categorized["unique_combos"]

        self._mode_cache[mode] = categorized

        combo_window = settings.get("user.input_map_combo_window", 300)
        self.combo_window = f"{combo_window}ms"

    def setup(self, input_map):
        self.input_map_user_ref = input_map
        self._mode_cache = {}
        if "default" in input_map:
            self.setup_mode("default")
        else:
            self.setup_mode(None)

    def _delayed_combo_execute(self):
        if self.combo_job:
            cron.cancel(self.combo_job)
            self.combo_job = None
        if not self.pending_combo:
            self.combo_chain = ""
            self.pending_combo = None
            return
        # Store pending_combo locally to avoid race condition if action() triggers another event
        pending = self.pending_combo
        self.combo_chain = ""
        self.pending_combo = None
        # Try conditional first, fall through to unconditional
        if self.has_conditions and self._dispatch_conditional(pending, self.delayed_conditional):
            return
        if pending not in self.delayed_commands:
            return
        action_tuple = self.delayed_commands[pending]
        command = action_tuple[0]
        action_func = action_tuple[1]
        throttled = self._throttle_busy.get(pending)
        action_func()
        if not throttled:
            self._trigger_event(pending, command)

    def _delayed_potential_combo(self):
        if self.combo_job:
            cron.cancel(self.combo_job)
            self.combo_job = None

        # maybe needed for variable patterns
        # if self.combo_chain and self.combo_chain in self.immediate_commands:
        #     action = self.immediate_commands[self.combo_chain][1]
        #     throttled = self._throttle_busy.get(self.combo_chain)
        #     action()
        #     if not throttled:
        #         command = self.immediate_commands[self.combo_chain][0]
        #         input_map_event_trigger(self.combo_chain, command)

        self.combo_chain = ""
        self.pending_combo = None

    def _try_conditional(self, input_chain: str, conditional_dict: dict) -> bool:
        """Try conditional entries for input_chain. First match wins. Returns True if matched."""
        entries = conditional_dict.get(input_chain)
        if not entries:
            return False
        for conditions, action_tuple in entries:
            if evaluate_conditions(conditions, self._context):
                command = action_tuple[0]
                action_func = action_tuple[1]
                throttled = self._throttle_busy.get(input_chain)
                action_func()
                if not throttled:
                    self._trigger_event(input_chain, command)
                return True
        return False

    def _try_conditional_edge(self, input_chain: str, conditional_dict: dict) -> bool:
        """Edge-triggered conditional: only fire when the active region changes."""
        entries = conditional_dict.get(input_chain)
        if entries is None:
            entries = []

        new_region = None
        matched_action = None
        for idx, (conditions, action_tuple) in enumerate(entries):
            if evaluate_conditions(conditions, self._context):
                new_region = idx
                matched_action = action_tuple
                break

        if new_region is None:
            if input_chain in self._edge_else_actions:
                new_region = _REGION_ELSE
                matched_action = self._edge_else_actions[input_chain]
            else:
                return False

        prev_region = self._active_region.get(input_chain)
        if new_region == prev_region:
            return True  # Consumed but suppressed (same region)

        self._active_region[input_chain] = new_region
        command = matched_action[0]
        action_func = matched_action[1]
        throttled = self._throttle_busy.get(input_chain)
        action_func()
        if not throttled:
            self._trigger_event(input_chain, command)
        return True

    def _dispatch_conditional(self, input_chain: str, conditional_dict: dict) -> bool:
        if self.has_edge_triggered and input_chain in self._edge_triggered_bases:
            return self._try_conditional_edge(input_chain, conditional_dict)
        return self._try_conditional(input_chain, conditional_dict)

    def _try_variable_patterns(self, input_chain: str, pattern_dict: dict) -> bool:
        for pattern, action in pattern_dict.items():
            variables = match_variable_pattern(input_chain, pattern)
            if variables is not None:
                execute_variable_action(action, variables)
                command = action[0]
                self._trigger_event(pattern, command)
                return True
        return False

    def _prepare_delayed_command(self):
        self.pending_combo = self.combo_chain
        self.combo_job = cron.after(self.combo_window, self._delayed_combo_execute)

    def _execute_delayed_variable_command(self):
        self.pending_combo = self.combo_chain
        self.combo_job = cron.after(self.combo_window, self._delayed_combo_execute_variable)

    def _delayed_combo_execute_variable(self):
        if self.combo_job:
            cron.cancel(self.combo_job)
            self.combo_job = None
        # Try to match the pending combo against delayed variable patterns
        matched = self._try_variable_patterns(self.pending_combo, self.delayed_variable_patterns)
        self.combo_chain = ""
        self.pending_combo = None

    def _execute_immediate_command(self, input_name: str, clear_chain: bool = True):
        combo_chain = self.combo_chain
        action_tuple = self.immediate_commands[combo_chain]
        command = action_tuple[0]
        action_func = action_tuple[1]
        try:
            throttled = self._throttle_busy.get(input_name)
            action_func()
            if not throttled:
                self._trigger_event(combo_chain, command)

            # if our combo ends in a continuous input, we should force
            # a throttle so there is clear separation between the combo
            # and a followup input.
            if combo_chain in self.unique_combos:
                last_input = combo_chain.split(' ')[-1]
                if last_input in self.base_pairs:
                    input_map_throttle(90, last_input, lambda: None, self._throttle_busy)
                    input_map_throttle(90, f"{last_input}_stop", lambda: None, self._throttle_busy)
        finally:
            if clear_chain:
                self.combo_chain = ""
                self.pending_combo = None

    def _execute_immediate_variable_pattern(self):
        self.combo_chain = ""
        self.pending_combo = None

    def _execute_single_immediate_command(self, input: str):
        if self.pending_combo:
            self._delayed_combo_execute()
            actions.sleep("20ms")
        action_tuple = self.immediate_commands[input]
        command = action_tuple[0]
        action_func = action_tuple[1]
        throttled = self._throttle_busy.get(input)
        # Clear state before executing to prevent race conditions with rapid input
        self.combo_chain = ""
        self.pending_combo = None
        action_func()
        if not throttled:
            self._trigger_event(input, command)

    def _could_be_variable_pattern_start(self, combo_chain: str) -> bool:
        """Check if the current combo chain could be the start of a variable pattern"""
        if not self.has_variables:
            return False

        # Check immediate variable patterns
        for pattern in self.immediate_variable_patterns.keys():
            pattern_parts = pattern.split()
            combo_parts = combo_chain.split()

            # If we have fewer parts than the pattern and they match so far, it could be a start
            if len(combo_parts) < len(pattern_parts):
                matches_so_far = True
                for i, combo_part in enumerate(combo_parts):
                    pattern_part = pattern_parts[i]
                    if not pattern_part.startswith('$') and pattern_part != combo_part:
                        matches_so_far = False
                        break
                if matches_so_far:
                    return True

        # Check delayed variable patterns
        for pattern in self.delayed_variable_patterns.keys():
            pattern_parts = pattern.split()
            combo_parts = combo_chain.split()

            # If we have fewer parts than the pattern and they match so far, it could be a start
            if len(combo_parts) < len(pattern_parts):
                matches_so_far = True
                for i, combo_part in enumerate(combo_parts):
                    pattern_part = pattern_parts[i]
                    if not pattern_part.startswith('$') and pattern_part != combo_part:
                        matches_so_far = False
                        break
                if matches_so_far:
                    return True

        return False

    def _execute_potential_combo(self):
        self.combo_job = cron.after(self.combo_window, self._delayed_potential_combo)

    def execute(
        self,
        input_name: str,
        power: float = None,
        f0: float = None,
        f1: float = None,
        f2: float = None,
        x: float = None,
        y: float = None,
        value: float = None
    ):
        # Store input context for actions and condition evaluation
        self._context.update(power=power, f0=f0, f1=f1, f2=f2, x=x, y=y, value=value)

        if input_name not in self.base_inputs:
            return

        if input_name in self.base_pairs:
            if self._debounce_busy.get(f"{input_name}_stop"):
                cron.cancel(self._debounce_busy[f"{input_name}_stop"])
                self._debounce_busy[f"{input_name}_stop"] = False
                return

        if self.combo_job:
            cron.cancel(self.combo_job)
            self.combo_job = None

        self.combo_chain = self.combo_chain + f" {input_name}" if self.combo_chain else input_name

        if self.combo_chain in self.delayed_commands or (self.has_conditions and self.combo_chain in self.delayed_conditional):
            if self.combo_chain in self.immediate_commands:
                # possible if we have a ":now" defined
                self._execute_immediate_command(input_name, clear_chain=False)
            self._prepare_delayed_command()
        elif self.has_conditions and self.combo_chain in self.immediate_conditional:
            matched = self._dispatch_conditional(self.combo_chain, self.immediate_conditional)
            if not matched and self.combo_chain in self.immediate_commands:
                self._execute_immediate_command(input_name)
            else:
                self.combo_chain = ""
                self.pending_combo = None
        elif self.combo_chain in self.immediate_commands:
            if self._could_be_variable_pattern_start(self.combo_chain):
                self._execute_potential_combo()
            else:
                self._execute_immediate_command(input_name)
        elif self.has_variables and self._try_variable_patterns(self.combo_chain, self.immediate_variable_patterns):
            self._execute_immediate_variable_pattern()
        elif self.has_variables and self._try_variable_patterns(self.combo_chain, self.delayed_variable_patterns):
            self._execute_delayed_variable_command()
        # Fallback to single input_name commands
        elif self.has_conditions and input_name in self.immediate_conditional:
            if self.pending_combo:
                self._delayed_combo_execute()
                actions.sleep("20ms")
            matched = self._dispatch_conditional(input_name, self.immediate_conditional)
            if not matched and input_name in self.immediate_commands:
                self._execute_single_immediate_command(input_name)
            else:
                self.combo_chain = ""
                self.pending_combo = None
        elif input_name in self.immediate_commands:
            self._execute_single_immediate_command(input_name)
        else:
            self._execute_potential_combo()

# todo: try using the user's direct reference instead
input_map_saved = InputMap()

def input_map_throttle(time_ms: int, single_input: str, command: callable, throttle_busy: dict):
    """Throttle the command once every time_ms"""
    if throttle_busy.get(single_input):
        return
    throttle_busy[single_input] = True
    command()
    cron.after(f"{time_ms}ms", lambda: throttle_busy.__setitem__(single_input, False))

def input_map_debounce(time_ms: int, id: str, command: callable, debounce_busy: dict):
    """Debounce"""
    if debounce_busy.get(id):
        cron.cancel(debounce_busy[id])
    debounce_busy[id] = cron.after(f"{time_ms}ms", lambda: (command(), debounce_busy.__setitem__(id, False)))

def input_map_handle(
    input_name: str,
    power: float = None,
    f0: float = None,
    f1: float = None,
    f2: float = None,
    x: float = None,
    y: float = None,
    value: float = None
):
    input_map = actions.user.input_map()
    if input_map_saved.input_map_user_ref != input_map:
        print("init input map")
        input_map_saved.setup(input_map)

    input_map_saved.execute(input_name, power=power, f0=f0, f1=f1, f2=f2, x=x, y=y, value=value)

def input_map_event_register(on_input: callable):
    event_subscribers.append(on_input)

def input_map_event_unregister(on_input: callable):
    try:
        event_subscribers.remove(on_input)
    except ValueError:
        # we may have lost the reference
        # see if the callback looks like one of the subscribers
        for subscriber in event_subscribers:
            if subscriber.__name__ == on_input.__name__:
                event_subscribers.remove(subscriber)
                break

def input_map_event_trigger(event: dict):
    for on_input_subscriber in event_subscribers:
        on_input_subscriber(event)

def input_map_mode_get() -> str:
    return input_map_saved.current_mode

def input_map_mode_set(mode: str):
    config = actions.user.input_map()
    if mode in config:
        input_map_saved.setup_mode(mode)
    else:
        raise ValueError(f"Mode '{mode}' not found in input_map")

def input_map_mode_cycle() -> str:
    config = actions.user.input_map()
    modes = list(config.keys())
    current_mode = input_map_mode_get()
    if current_mode in modes:
        current_index = modes.index(current_mode)
        next_index = (current_index + 1) % len(modes)
        next_mode = modes[next_index]
        input_map_mode_set(next_mode)
        return next_mode
    else:
        raise ValueError(f"Mode '{current_mode}' not found in input_map")

def input_map_get(mode: str = None) -> dict:
    """Get the input map dict for the current or specified mode."""
    input_map = actions.user.input_map()
    if mode:
        if mode in input_map:
            return input_map[mode]
        raise ValueError(f"Mode '{mode}' not found in input_map")
    return input_map
