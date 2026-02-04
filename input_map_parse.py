"""
Parsing, validation, and categorization for input_map.
This module handles setup-time processing (cold path).
"""
import re
import inspect

def get_base_input(input):
    """The part before colon e.g. 'pop' in 'pop:db_170'"""
    base_combo = input.split(':')[0]
    base_inputs = base_combo.split(' ')
    return base_combo.strip(), base_inputs

def get_modified_action(input, action, throttle_busy, debounce_busy):
    # Late import to avoid circular dependency
    from .input_map import input_map_throttle, input_map_debounce

    if ":th" in input:
        match = re.search(r':th_(\d+)', input)
        throttle_amount = int(match.group(1)) if match else 100
        base_input = input.replace(f":th_{throttle_amount}", "")
        return (action[0], lambda: input_map_throttle(throttle_amount, base_input, action[1], throttle_busy))
    if ":db" in input:
        match = re.search(r':db_(\d+)', input)
        debounce_amount = int(match.group(1)) if match else 100
        base_input = input.replace(f":db_{debounce_amount}", "")
        return (action[0], lambda: input_map_debounce(debounce_amount, base_input, action[1], debounce_busy))
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

def process_command_categorization(input, action, base_input_map, combo_input_set, immediate_commands, delayed_commands, throttle_busy, debounce_busy):
    modified_action = get_modified_action(input, action, throttle_busy, debounce_busy)
    base = base_input_map[input]

    if any(other_input.startswith(f"{base} ") and other_input != base for other_input in combo_input_set):
        if ":now" in input:
            delayed_commands[base] = modified_action
            immediate_commands[base] = modified_action
        else:
            delayed_commands[base] = modified_action
    else:
        immediate_commands[base] = modified_action

def process_variable_categorization(input_pattern, action, variable_commands, combo_input_set, immediate_variable_patterns, delayed_variable_patterns, throttle_busy, debounce_busy):
    modified_action = get_modified_action(input_pattern, action, throttle_busy, debounce_busy)
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

def categorize_commands(commands, throttle_busy, debounce_busy):
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
        process_command_categorization(input, action, base_input_map, combo_input_set, immediate_commands, delayed_commands, throttle_busy, debounce_busy)

    for input_pattern, action in variable_commands:
        process_variable_categorization(input_pattern, action, variable_commands, combo_input_set, immediate_variable_patterns, delayed_variable_patterns, throttle_busy, debounce_busy)

    has_vars = bool(immediate_variable_patterns or delayed_variable_patterns)

    return {
        "immediate_commands": immediate_commands,
        "delayed_commands": delayed_commands,
        "immediate_variable_patterns": immediate_variable_patterns,
        "delayed_variable_patterns": delayed_variable_patterns,
        "base_input_set": base_input_set,
        "base_pairs": base_pairs,
        "unique_combos": unique_combos,
        "has_variables": has_vars
    }
