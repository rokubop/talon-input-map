from talon import Module, actions, cron, ui, ctrl, settings
import re
import inspect
mod = Module()

event_subscribers = []

mod.setting("input_map_combo_window", type=int, default=300, desc="The time window to wait for a combo to complete")

def get_base_input(input):
    """The part before colon e.g. 'pop' in 'pop:db_170'"""
    base_combo = input.split(':')[0]
    base_inputs = base_combo.split(' ')
    return base_combo.strip(), base_inputs

def get_modified_action(input, action):
    if ":th" in input:
        match = re.search(r':th_(\d+)', input)
        throttle_amount = int(match.group(1)) if match else 100
        base_input = input.replace(f":th_{throttle_amount}", "")
        return (action[0], lambda: input_map_throttle(throttle_amount, base_input, action[1]))
    if ":db" in input:
        match = re.search(r':db_(\d+)', input)
        debounce_amount = int(match.group(1)) if match else 100
        base_input = input.replace(f":db_{debounce_amount}", "")
        return (action[0], lambda: input_map_debounce(debounce_amount, base_input, action[1]))
    return action

def has_variables(input_pattern: str) -> bool:
    return '$' in input_pattern

def extract_variables(input_pattern: str) -> list[str]:
    variables = re.findall(r'\$([a-zA-Z_][a-zA-Z0-9_]*)', input_pattern)
    return variables

def pattern_to_regex(input_pattern: str) -> str:
    escaped = re.escape(input_pattern)
    # Replace escaped variable placeholders with regex groups
    # Use a lambda to avoid backslash interpretation issues
    pattern = re.sub(r'\\\$[a-zA-Z_][a-zA-Z0-9_]*', lambda m: r'(\w+)', escaped)
    return pattern

def validate_variable_action(input_pattern: str, action: tuple) -> bool:
    if not isinstance(action, tuple) or len(action) < 2:
        return False

    variables = extract_variables(input_pattern)
    lambda_func = action[1]

    if not callable(lambda_func):
        return False

    try:
        sig = inspect.signature(lambda_func)
        param_count = len(sig.parameters)
        variable_count = len(variables)
        return param_count == 0 or param_count == variable_count
    except (ValueError, TypeError):
        return True

def match_variable_pattern(input: str, pattern: str) -> dict[str, str] | None:
    regex_pattern = pattern_to_regex(pattern)
    match = re.match(f'^{regex_pattern}$', input)

    if not match:
        return None

    variables = extract_variables(pattern)
    values = match.groups()

    if len(variables) != len(values):
        return None

    result = dict(zip(variables, values))
    return result

def execute_variable_action(action: tuple, variables: dict[str, str]):
    lambda_func = action[1]

    try:
        sig = inspect.signature(lambda_func)
        param_count = len(sig.parameters)

        if param_count == 0:
            return lambda_func()
        else:
            var_values = list(variables.values())
            return lambda_func(*var_values)
    except (ValueError, TypeError):
        return lambda_func()

def process_command_categorization(input, action, base_input_map, combo_input_set, immediate_commands, delayed_commands):
    modified_action = get_modified_action(input, action)
    base = base_input_map[input]

    if any(other_input.startswith(f"{base} ") and other_input != base for other_input in combo_input_set):
        if ":now" in input:
            delayed_commands[base] = modified_action
            immediate_commands[base] = modified_action
        else:
            delayed_commands[base] = modified_action
    else:
        immediate_commands[base] = modified_action

def process_variable_categorization(input_pattern, action, variable_commands, combo_input_set, immediate_variable_patterns, delayed_variable_patterns):
    modified_action = get_modified_action(input_pattern, action)
    base_pattern = get_base_input(input_pattern)[0]

    is_delayed = False

    # Check if any other variable patterns could conflict with this one
    # (i.e., this pattern is a prefix of another pattern)
    for other_pattern, _ in variable_commands:
        other_base = get_base_input(other_pattern)[0]
        if other_pattern != input_pattern and other_base.startswith(f"{base_pattern} "):
            is_delayed = True
            break

    # Check if any static combos could conflict with this pattern
    # (i.e., this pattern is a prefix of a static combo)
    if not is_delayed:
        for static_combo in combo_input_set:
            if static_combo.startswith(f"{base_pattern} ") and static_combo != base_pattern:
                is_delayed = True
                break

    if is_delayed:
        delayed_variable_patterns[input_pattern] = modified_action
    else:
        immediate_variable_patterns[input_pattern] = modified_action

def categorize_commands(commands):
    immediate_commands = {}
    delayed_commands = {}
    immediate_variable_patterns = {}
    delayed_variable_patterns = {}
    base_pairs = set()
    combo_input_set = set()
    base_input_set = set()
    unique_combos = set()
    base_input_map = {}
    active_commands = []
    variable_commands = []

    for input, action in commands.items():
        if not input or not isinstance(action, tuple) or len(action) < 2:
            continue

        try:
            if action[1] is None or not callable(action[1]):
                raise ValueError(
                    f"\nThe action for '{input}' must be a callable (function or lambda).\n\n"
                    f"Valid examples:\n"
                    f'"pop": ("E", lambda: actions.user.game_key("e")),\n'
                    f'"pop": ("L click", actions.user.game_mouse_click_left),\n\n'
                    f"Invalid examples:\n"
                    f'"pop": ("E", actions.user.game_key("e")),\n'
                    f'"pop": ("L click", actions.user.game_mouse_click_left())\n'
                )
        except ValueError as e:
            print(e)
            continue

        if has_variables(input):
            if not validate_variable_action(input, action):
                print(f"Warning: Variable pattern '{input}' has mismatched lambda signature")
                continue
            variable_commands.append((input, action))
        else:
            base_combo, base_inputs = get_base_input(input)

            if "_stop" in input and len(base_inputs) == 1:
                base_pairs.add(base_inputs[0].replace("_stop", ""))

            if len(base_inputs) > 1:
                unique_combos.add(base_combo)

            for base_input in base_inputs:
                base_input_set.add(base_input)

            combo_input_set.add(base_combo)
            base_input_map[input] = base_combo
            active_commands.append((input, action))

    # Also add base inputs from variable patterns
    for input_pattern, action in variable_commands:
        base_combo, base_inputs = get_base_input(input_pattern)
        for base_input in base_inputs:
            # Only add if it's not a variable placeholder
            if not base_input.startswith('$'):
                base_input_set.add(base_input)

    for input, action in active_commands:
        process_command_categorization(input, action, base_input_map, combo_input_set, immediate_commands, delayed_commands)

    for input_pattern, action in variable_commands:
        process_variable_categorization(input_pattern, action, variable_commands, combo_input_set, immediate_variable_patterns, delayed_variable_patterns)

    return {
        "immediate_commands": immediate_commands,
        "delayed_commands": delayed_commands,
        "immediate_variable_patterns": immediate_variable_patterns,
        "delayed_variable_patterns": delayed_variable_patterns,
        "base_input_set": base_input_set,
        "base_pairs": base_pairs,
        "unique_combos": unique_combos
    }

class InputMap():
    def __init__(self):
        self.input_map_user_ref = None
        self.current_mode = None
        self.immediate_commands = {}
        self.delayed_commands = {}
        self.immediate_variable_patterns = {}
        self.delayed_variable_patterns = {}
        self.has_variables = False
        self.base_pairs = set()
        self.combo_chain = ""
        self.combo_job = None
        self.base_inputs = None
        self.pending_combo = None
        self.combo_window = "300ms"
        self.unique_combos = set()

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
        commands = input_map.get("commands", {}) if "commands" in input_map else input_map

        categorized = categorize_commands(commands)
        self.immediate_commands = categorized["immediate_commands"]
        self.delayed_commands = categorized["delayed_commands"]
        self.immediate_variable_patterns = categorized["immediate_variable_patterns"]
        self.delayed_variable_patterns = categorized["delayed_variable_patterns"]
        self.has_variables = bool(self.immediate_variable_patterns or self.delayed_variable_patterns)
        self.base_inputs = categorized["base_input_set"]
        self.base_pairs = categorized["base_pairs"]
        self.unique_combos = categorized["unique_combos"]

        combo_window = settings.get("user.input_map_combo_window", 300)
        self.combo_window = f"{combo_window}ms"

    def setup(self, input_map):
        self.input_map_user_ref = input_map
        if "default" in input_map:
            self.setup_mode("default")
        else:
            self.setup_mode(None)

    def _delayed_combo_execute(self):
        if self.combo_job:
            cron.cancel(self.combo_job)
            self.combo_job = None
        if not self.pending_combo or self.pending_combo not in self.delayed_commands:
            self.combo_chain = ""
            self.pending_combo = None
            return
        # Store pending_combo locally to avoid race condition if action() triggers another event
        pending = self.pending_combo
        action = self.delayed_commands[pending][1]
        throttled = input_map_throttle_busy.get(pending)
        self.combo_chain = ""
        self.pending_combo = None
        action()
        if not throttled:
            command = self.delayed_commands[pending][0]
            input_map_event_trigger(pending, command)

    def _delayed_potential_combo(self):
        if self.combo_job:
            cron.cancel(self.combo_job)
            self.combo_job = None

        # maybe needed for variable patterns
        # if self.combo_chain and self.combo_chain in self.immediate_commands:
        #     action = self.immediate_commands[self.combo_chain][1]
        #     throttled = input_map_throttle_busy.get(self.combo_chain)
        #     action()
        #     if not throttled:
        #         command = self.immediate_commands[self.combo_chain][0]
        #         input_map_event_trigger(self.combo_chain, command)

        self.combo_chain = ""
        self.pending_combo = None

    def _try_variable_patterns(self, input_chain: str, pattern_dict: dict) -> bool:
        for pattern, action in pattern_dict.items():
            variables = match_variable_pattern(input_chain, pattern)
            if variables is not None:
                execute_variable_action(action, variables)
                command = action[0]
                input_map_event_trigger(pattern, command)
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

    def _execute_action(self, input_name: str):
        """Execute action for a combo without clearing combo_chain state"""
        if not self.combo_chain or self.combo_chain not in self.immediate_commands:
            return

        try:
            action = self.immediate_commands[self.combo_chain][1]
            throttled = input_map_throttle_busy.get(input_name)
            action()
            if not throttled:
                command = self.immediate_commands[self.combo_chain][0]
                input_map_event_trigger(self.combo_chain, command)

            # if our combo ends in a continuous input, we should force
            # a throttle so there is clear separation between the combo
            # and a followup input.
            if self.combo_chain in self.unique_combos:
                last_input = self.combo_chain.split(' ')[-1]
                if last_input in self.base_pairs:
                    input_map_throttle(90, last_input, lambda: None)
                    input_map_throttle(90, f"{last_input}_stop", lambda: None)
        except Exception:
            import traceback
            print(f"Error executing action '{self.combo_chain}':")
            traceback.print_exc()

    def _execute_immediate_command(self, input_name: str):
        try:
            self._execute_action(input_name)
        finally:
            self.combo_chain = ""
            self.pending_combo = None

    def _execute_immediate_variable_pattern(self):
        self.combo_chain = ""
        self.pending_combo = None

    def _execute_single_immediate_command(self, input: str):
        if self.pending_combo:
            self._delayed_combo_execute()
            actions.sleep("20ms")
        action = self.immediate_commands[input][1]
        throttled = input_map_throttle_busy.get(input)
        # Clear state before executing to prevent race conditions with rapid input
        self.combo_chain = ""
        self.pending_combo = None
        action()
        if not throttled:
            command = self.immediate_commands[input][0]
            input_map_event_trigger(input, command)

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

    def execute(self, input_name: str):
        global input_map_debounce_busy

        if input_name not in self.base_inputs:
            return

        if input_name in self.base_pairs:
            if input_map_debounce_busy.get(f"{input_name}_stop"):
                cron.cancel(input_map_debounce_busy[f"{input_name}_stop"])
                input_map_debounce_busy[f"{input_name}_stop"] = False
                return

        if self.combo_job:
            cron.cancel(self.combo_job)
            self.combo_job = None

        self.combo_chain = self.combo_chain + f" {input_name}" if self.combo_chain else input_name

        if self.combo_chain in self.delayed_commands:
            if self.combo_chain in self.immediate_commands:
                # possible if we have a ":now" defined
                self._execute_action(input_name)
            self._prepare_delayed_command()
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
        elif input_name in self.immediate_commands:
            self._execute_single_immediate_command(input_name)
        else:
            self._execute_potential_combo()

# todo: try using the user's direct reference instead
input_map_saved = InputMap()

input_map_throttle_busy = {}
input_map_debounce_busy = {}

def input_map_throttle_disable(id):
    global input_map_throttle_busy
    input_map_throttle_busy[id] = False

def input_map_throttle(time_ms: int, single_input: str, command: callable):
    """Throttle the command once every time_ms"""
    global input_map_throttle_busy
    if input_map_throttle_busy.get(single_input):
        return
    input_map_throttle_busy[single_input] = True
    command()
    cron.after(f"{time_ms}ms", lambda: input_map_throttle_disable(single_input))

def input_map_debounce_disable(id):
    global input_map_debounce_busy
    input_map_debounce_busy[id] = False

def input_map_debounce(time_ms: int, id: str, command: callable):
    """Debounce"""
    global input_map_debounce_busy
    if input_map_debounce_busy.get(id):
        cron.cancel(input_map_debounce_busy[id])
    input_map_debounce_busy[id] = cron.after(f"{time_ms}ms", lambda: (command(), input_map_debounce_disable(id)))

def input_map_handle(input_name: str):
    input_map = actions.user.input_map()
    if input_map_saved.input_map_user_ref != input_map:
        print("init input map")
        input_map_saved.setup(input_map)

    input_map_saved.execute(input_name)

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

def input_map_event_trigger(input: str, command: str):
    for on_input_subscriber in event_subscribers:
        on_input_subscriber(input, command)

def input_map_get_mode() -> str:
    return input_map_saved.current_mode

def input_map_set_mode(mode: str):
    config = actions.user.input_map()
    if mode in config:
        # probably need to build a queue for this instead
        cron.after("30ms", lambda: input_map_saved.setup_mode(mode))
    else:
        raise ValueError(f"Mode '{mode}' not found in input_map")

def input_map_cycle_mode() -> str:
    config = actions.user.input_map()
    modes = list(config.keys())
    current_mode = input_map_get_mode()
    if current_mode in modes:
        current_index = modes.index(current_mode)
        next_index = (current_index + 1) % len(modes)
        next_mode = modes[next_index]
        input_map_set_mode(next_mode)
        return next_mode
    else:
        raise ValueError(f"Mode '{current_mode}' not found in input_map")
