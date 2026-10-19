"""
Parsing, validation, and categorization for input_map.
This module handles setup-time processing (cold path).
"""
import re
import inspect

# The language of an input map key, described. The parser below reads its
# patterns, names and defaults from these, and input_map_types() hands
# them out, so this is the one place each is written.

# The ':' segments a key can carry. `pattern` matches the whole segment,
# group 1 being its number when it takes one; a condition's groups are
# variable, operator, number.
SEGMENTS = {
    "th": {
        "desc": "Fires at once, then ignores this input until this long has passed.",
        "pattern": r"th(?:_(\d+))?",
        "unit": "ms",
        "default": 100,
    },
    "db": {
        "desc": "Waits this long before firing, starting over each time the input comes again. "
                "On a stop: a start inside the wait cancels the stop and is skipped too, so a "
                "brief gap doesn't count as letting go. On a start whose stop is debounced too: "
                "a stop inside the wait cancels both.",
        "pattern": r"db(?:_(\d+))?",
        "unit": "ms",
        "default": 100,
    },
    "now": {
        "desc": "Fires at once even when a combo starting with this input could still follow, "
                "and still tracks the combo. Without it the first input of a combo waits out "
                "the combo window.",
        "pattern": r"now",
    },
    "after": {
        "desc": "Fires this long after the input, as well as the plain binding, unless a combo "
                "uses the input first. The input coming again starts the wait over. One per "
                "input, and it takes no conditions, throttle or debounce: those are dropped.",
        "pattern": r"after_(\d+)",
        "unit": "ms",
    },
    "init": {
        "desc": "Used in place of the plain binding for this long after the mode is entered. "
                "Pair it with a plain key; not with else.",
        "pattern": r"init(?:_(\d+))?",
        "unit": "ms",
        "default_setting": "user.input_map_init_window",
    },
    "condition": {
        "desc": "Fires only while the variable compares true against the number. Several on "
                "one key all have to hold.",
        # Filled in below, from CONDITION_VARIABLES and OPERATORS
        "pattern": "",
    },
    "else": {
        "desc": "Fires when none of this input's conditions hold. Makes them edge-triggered: "
                "once per change of which one holds, not on every event.",
        "pattern": r"else",
    },
}

# What a condition compares. `source` is which handle actions hand it over:
# parrot, xy or value; `stop` is measured by input_map on a release key.
CONDITION_VARIABLES = {
    "power": {"desc": "How loud the parrot noise is.", "source": "parrot"},
    "f0": {"desc": "The parrot noise's pitch.", "source": "parrot"},
    "f1": {"desc": "The parrot noise's first formant.", "source": "parrot"},
    "f2": {"desc": "The parrot noise's second formant.", "source": "parrot"},
    "x": {"desc": "Horizontal position, as from gaze.", "source": "xy"},
    "y": {"desc": "Vertical position, as from gaze.", "source": "xy"},
    "value": {"desc": "A value the input carries, as how far a face expression is made.",
              "source": "value"},
    "dur": {"desc": "How long since the input started, in ms. Only on its release key.",
            "source": "stop"},
}

OPERATORS = {
    ">": "greater than",
    "<": "less than",
    ">=": "at least",
    "<=": "at most",
    "==": "equal to",
    "!=": "not equal to",
}

# The end of an input's name that makes it the input letting go.
RELEASE_SUFFIXES = {
    "_stop": "When the input stops, e.g. hiss_stop.",
    "_up": "When the input is let go, e.g. a pedal's left_up.",
}

CONTEXT_KEYS = set(CONDITION_VARIABLES)
# Longest first, so '>=' is not read as '>'
_OPS = "|".join(re.escape(op) for op in sorted(OPERATORS, key=len, reverse=True))
_VARS = "|".join(CONDITION_VARIABLES)
SEGMENTS["condition"]["pattern"] = rf"({_VARS})({_OPS})(-?\d+(?:\.\d+)?)"
CONDITION_PATTERN = re.compile(rf"^{SEGMENTS['condition']['pattern']}$")
MISFORMATTED_CONDITION_PATTERN = re.compile(rf'({_OPS})\d')
MODIFIER_SEPARATOR = " + "
THROTTLE_DEFAULT_MS = SEGMENTS["th"]["default"]
DEBOUNCE_DEFAULT_MS = SEGMENTS["db"]["default"]

INIT_PATTERN = re.compile(rf"^{SEGMENTS['init']['pattern']}$")
MODE_AGE = "mode_age"
DEFAULT_INIT_WINDOW_MS = 300


LEGEND_HIDDEN_MODIFIERS = re.compile(r"^(th|db|now)(_\d+)?$")
LEGEND_AFTER_PATTERN = re.compile(rf"^{SEGMENTS['after']['pattern']}$")


def _legend_segment(segment: str):
    """One ':' segment as a legend token. Returns (variable, text)"""
    if LEGEND_HIDDEN_MODIFIERS.match(segment):
        return (None, None)
    match = LEGEND_AFTER_PATTERN.match(segment)
    if match:
        return (None, f"after {match.group(1)}")
    match = INIT_PATTERN.match(segment)
    if match:
        window = match.group(1)
        return (None, f"init {window}" if window else "init")
    match = CONDITION_PATTERN.match(segment)
    if match:
        return (match.group(1), f"{match.group(1)} {match.group(2)} {match.group(3)}")
    return (None, segment.replace("_", " "))


def build_legend(commands: dict) -> dict:
    """{input: label} for display, sized for a HUD column."""
    entries = []
    for input_key, action in commands.items():
        if isinstance(action, tuple):
            if len(action) == 0:
                continue
            label = action[0]
        else:
            label = action
        if label == "":
            continue
        base, *segments = input_key.split(":")
        tokens = [_legend_segment(s) for s in segments]
        entries.append((base, [t for t in tokens if t[1] is not None], label))

    base_counts = {}
    shared_vars = {}
    for base, tokens, _ in entries:
        base_counts[base] = base_counts.get(base, 0) + 1
        for variable, _text in tokens:
            if variable is not None:
                shared_vars.setdefault(base, set()).add(variable)

    legend = {}
    for base, tokens, label in entries:
        parts = [base.replace("_", " ")]
        if base_counts[base] > 1:
            elide = len(shared_vars.get(base, ())) == 1
            for variable, text in tokens:
                if variable is not None and elide:
                    text = text[len(variable) + 1:]
                parts.append(text)
        legend[" ".join(parts)] = label
    return legend


def set_default_init_window(ms: int):
    """Baked into the condition at parse time, so call before categorizing."""
    global DEFAULT_INIT_WINDOW_MS
    DEFAULT_INIT_WINDOW_MS = int(ms)


def has_modifier(key: str) -> bool:
    """Check if an input key uses the cross-input modifier syntax ('a + b')."""
    return MODIFIER_SEPARATOR in key


def extract_modifier(key: str) -> tuple:
    """Split 'pedal_left + pop' into ('pedal_left', 'pop').
    Returns (modifier_name, activator_key)."""
    parts = key.split(MODIFIER_SEPARATOR, 1)
    return parts[0].strip(), parts[1].strip()


def validate_modifier(name: str, base_pairs: set, edge_triggered_bases: set):
    """Ensure a modifier name is stateful (has start/stop pair or edge-triggered conditions)."""
    if name not in base_pairs and name not in edge_triggered_bases:
        raise ValueError(
            f"\nModifier '{name}' is not stateful. "
            f"Modifiers must have a '_stop' or '_up' pair or if/else edge-triggered conditions.\n"
            f"Defined base_pairs: {base_pairs}\n"
            f"Defined edge_triggered_bases: {edge_triggered_bases}\n"
        )

def validate_input_format(input_key: str):
    """Warn if an input key looks like it has a misformatted condition."""
    base = input_key.split(':')[0]
    for part in base.split():
        if MISFORMATTED_CONDITION_PATTERN.search(part):
            match = re.match(rf'^(.*?)({_OPS})(.*)', part)
            if match and match.group(1) not in CONTEXT_KEYS:
                print(
                    f"\nWarning: '{input_key}' looks like it contains a condition "
                    f"but '{match.group(1)}' is not a condition variable.\n"
                    f"Did you mean: '{match.group(1)}:value{match.group(2)}{match.group(3)}'?\n"
                    f"Valid condition format: 'input_name:variable>threshold'\n"
                    f"Valid variables: {', '.join(CONDITION_VARIABLES)}\n"
                )

def parse_condition(segment: str):
    """Parse a single segment like 'power>10' into ('power', '>', 10.0), or None
    if not a condition. ':init' and ':init_300' desugar to a mode_age condition."""
    match = INIT_PATTERN.match(segment)
    if match:
        window = match.group(1)
        return (MODE_AGE, '<', float(window) if window else float(DEFAULT_INIT_WINDOW_MS))
    match = CONDITION_PATTERN.match(segment)
    if match:
        return (match.group(1), match.group(2), float(match.group(3)))
    return None

def extract_conditions(input_key: str):
    """Split 'pop:power>10:db_100' into ('pop:db_100', [('power', '>', 10.0)]).
    For 'gaze:else:db_100', returns ('gaze:db_100', None) where None signals else."""
    parts = input_key.split(':')
    conditions = []
    non_condition_parts = []
    is_else = False
    for part in parts:
        if part == "else":
            is_else = True
            continue
        parsed = parse_condition(part)
        if parsed:
            conditions.append(parsed)
        else:
            non_condition_parts.append(part)
    cleaned_key = ':'.join(non_condition_parts)
    if is_else:
        return cleaned_key, None
    return cleaned_key, conditions

def has_conditions(input_key: str) -> bool:
    """Quick check if an input key contains condition segments."""
    parts = input_key.split(':')
    for part in parts:
        if parse_condition(part) is not None:
            return True
        if part == "else":
            return True
    return False

def validate_conditions_no_overlap(conditional_entries: dict):
    """Error on duplicate condition sets for same base input."""
    for base_key, entries in conditional_entries.items():
        seen = []
        for conditions, _ in entries:
            cond_set = frozenset(conditions)
            if cond_set in seen:
                raise ValueError(f"Duplicate condition set for '{base_key}': {conditions}")
            seen.append(cond_set)

def detect_edge_triggered(conditional_dict: dict):
    """Scan for 'else' markers (conditions=None). Remove them from conditional_dict
    in place. Returns (edge_bases set, else_actions dict)."""
    edge_bases = set()
    else_actions = {}
    for base_key, entries in list(conditional_dict.items()):
        remaining = []
        for conditions, action_tuple in entries:
            if conditions is None:
                edge_bases.add(base_key)
                else_actions[base_key] = action_tuple
            else:
                remaining.append((conditions, action_tuple))
        conditional_dict[base_key] = remaining
    return edge_bases, else_actions

def evaluate_conditions(conditions: list, context: dict) -> bool:
    """Evaluate all conditions against context. Returns False if any context value is None."""
    for var, op, threshold in conditions:
        val = context.get(var)
        if val is None:
            return False
        if op == '>':
            if not (val > threshold):
                return False
        elif op == '<':
            if not (val < threshold):
                return False
        elif op == '>=':
            if not (val >= threshold):
                return False
        elif op == '<=':
            if not (val <= threshold):
                return False
        elif op == '==':
            if not (val == threshold):
                return False
        elif op == '!=':
            if not (val != threshold):
                return False
    return True

def get_base_input(input):
    """The part before colon e.g. 'pop' in 'pop:db_170'"""
    base_combo = input.split(':')[0]
    base_inputs = base_combo.split(' ')
    return base_combo.strip(), base_inputs

def parse_segment(segment: str, init_window_ms: int = None) -> dict:
    """One ':' segment, read the way SEGMENTS says.
    'th_90' -> {"id": "th", "text": "th_90", "value": 90, "ms": 90}
    'th' -> value None, ms the default. 'power>10' -> value ["power", ">", 10.0].
    A segment it doesn't know has id ""."""
    out = {"id": "", "text": segment, "value": None}
    for seg_id, seg in SEGMENTS.items():
        match = re.fullmatch(seg["pattern"], segment)
        if not match:
            continue
        out["id"] = seg_id
        if seg_id == "condition":
            out["value"] = [match.group(1), match.group(2), float(match.group(3))]
        elif seg.get("unit") == "ms":
            out["value"] = int(match.group(1)) if match.group(1) else None
            default = seg.get("default")
            if seg.get("default_setting"):
                default = DEFAULT_INIT_WINDOW_MS if init_window_ms is None else init_window_ms
            out["ms"] = out["value"] if out["value"] is not None else default
        break
    return out

def _parse_side(text: str, init_window_ms: int = None) -> dict:
    base, *segments = text.split(":")
    base = base.strip()
    inputs = base.split()
    release_suffix, release_of = "", ""
    if len(inputs) == 1:
        for suffix in RELEASE_SUFFIXES:
            if inputs[0].endswith(suffix):
                release_suffix, release_of = suffix, inputs[0][:-len(suffix)]
                break
    return {
        "base": base,
        "inputs": inputs,
        "release_suffix": release_suffix,
        "release_of": release_of,
        "variables": extract_variables(base),
        "segments": [parse_segment(s.strip(), init_window_ms) for s in segments],
    }

def parse_key(key: str, init_window_ms: int = None) -> dict:
    """What an input map key says, in parts.

    'pedal_left + pop pop:power>10:th_90' ->
        base "pop pop", inputs ["pop", "pop"], release_suffix "", release_of "",
        variables [], segments [condition, th],
        modifier {the same, for "pedal_left"}

    release_suffix is the end that makes it a release key ('_stop', '_up'),
    release_of the input it releases. A bare init's ms is init_window_ms,
    else the window last set."""
    modifier = None
    if has_modifier(key):
        modifier_raw, key_raw = extract_modifier(key)
        modifier = _parse_side(modifier_raw, init_window_ms)
    else:
        key_raw = key
    out = _parse_side(key_raw, init_window_ms)
    out["key"] = key
    out["modifier"] = modifier
    return out

def get_modified_action(input, action, throttle_busy, debounce_busy):
    # Late import to avoid circular dependency
    from .input_map import input_map_throttle, input_map_debounce

    if ":th" in input:
        match = re.search(r':th_(\d+)', input)
        throttle_amount = int(match.group(1)) if match else THROTTLE_DEFAULT_MS
        base_input = input.replace(f":th_{throttle_amount}", "")
        return (action[0], lambda: input_map_throttle(throttle_amount, base_input, action[1], throttle_busy))
    if ":db" in input:
        match = re.search(r':db_(\d+)', input)
        debounce_amount = int(match.group(1)) if match else DEBOUNCE_DEFAULT_MS
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

def wrap_with_context(action: tuple, context_ref: dict) -> tuple:
    """If callable has params matching context keys, wrap to pull from context_ref at call time."""
    func = action[1]
    if not callable(func):
        return action
    try:
        sig = inspect.signature(func)
        params = list(sig.parameters.keys())
    except (ValueError, TypeError):
        return action
    if not params or not all(p in CONTEXT_KEYS for p in params):
        return action
    def make_wrapper(original, param_names, ctx):
        def wrapper():
            return original(*[ctx.get(p) for p in param_names])
        return wrapper
    return (action[0], make_wrapper(func, params, context_ref))

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

def process_conditional_categorization(input, action, conditions, base_input_map, combo_input_set, immediate_conditional, delayed_conditional, throttle_busy, debounce_busy):
    modified_action = get_modified_action(input, action, throttle_busy, debounce_busy)
    base = base_input_map[input]

    if any(other_input.startswith(f"{base} ") and other_input != base for other_input in combo_input_set):
        delayed_conditional.setdefault(base, []).append((conditions, modified_action))
    else:
        immediate_conditional.setdefault(base, []).append((conditions, modified_action))

def categorize_commands(commands, throttle_busy, debounce_busy, context_ref=None):
    immediate_commands = {}
    delayed_commands = {}
    immediate_variable_patterns = {}
    delayed_variable_patterns = {}
    immediate_conditional = {}
    delayed_conditional = {}
    base_pairs = set()
    combo_input_set = set()
    base_input_set = set()
    unique_combos = set()
    base_input_map = {}
    active_commands = []
    variable_commands = []
    conditional_commands = []
    modifier_input_keys = []
    after_commands = {}

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

        if ":after_" in input:
            match = re.search(r':after_(\d+)', input)
            if match:
                after_ms = int(match.group(1))
                base_combo = get_base_input(input.split(':')[0])[0]
                if context_ref is not None:
                    action = wrap_with_context(action, context_ref)
                after_commands[base_combo] = (after_ms, action)
                for inp in base_combo.split():
                    base_input_set.add(inp)
                continue

        if has_modifier(input):
            modifier_input_keys.append((input, action))
            continue

        if has_variables(input):
            if not validate_variable_action(input, action):
                print(f"Warning: Variable pattern '{input}' has mismatched lambda signature")
                continue
            variable_commands.append((input, action))
        elif has_conditions(input):
            cleaned_key, conditions = extract_conditions(input)
            base_combo, base_inputs = get_base_input(cleaned_key)

            if len(base_inputs) == 1:
                inp0 = base_inputs[0]
                for suffix in RELEASE_SUFFIXES:
                    if inp0.endswith(suffix):
                        base_pairs.add(inp0[:-len(suffix)])
                        break

            if len(base_inputs) > 1:
                unique_combos.add(base_combo)

            for base_input in base_inputs:
                base_input_set.add(base_input)

            combo_input_set.add(base_combo)
            base_input_map[cleaned_key] = base_combo
            if context_ref is not None:
                action = wrap_with_context(action, context_ref)
            conditional_commands.append((cleaned_key, action, conditions))
        else:
            validate_input_format(input)
            base_combo, base_inputs = get_base_input(input)

            if len(base_inputs) == 1:
                inp0 = base_inputs[0]
                for suffix in RELEASE_SUFFIXES:
                    if inp0.endswith(suffix):
                        base_pairs.add(inp0[:-len(suffix)])
                        break

            if len(base_inputs) > 1:
                unique_combos.add(base_combo)

            for base_input in base_inputs:
                base_input_set.add(base_input)

            combo_input_set.add(base_combo)
            base_input_map[input] = base_combo
            if context_ref is not None:
                action = wrap_with_context(action, context_ref)
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

    for cleaned_key, action, conditions in conditional_commands:
        process_conditional_categorization(cleaned_key, action, conditions, base_input_map, combo_input_set, immediate_conditional, delayed_conditional, throttle_busy, debounce_busy)

    imm_edge_bases, imm_else_actions = detect_edge_triggered(immediate_conditional)
    del_edge_bases, del_else_actions = detect_edge_triggered(delayed_conditional)
    edge_triggered_bases = imm_edge_bases | del_edge_bases
    edge_else_actions = {**imm_else_actions, **del_else_actions}

    validate_conditions_no_overlap(immediate_conditional)
    validate_conditions_no_overlap(delayed_conditional)

    # Process deferred modifier keys (e.g. "pedal_left + pop", "gaze:x<500 + pop")
    modifier_commands = {}
    for raw_key, action in modifier_input_keys:
        modifier_raw, activator_raw = extract_modifier(raw_key)

        # Parse optional conditions from modifier side (e.g. "gaze:x<500" → "gaze", conditions)
        modifier_conditions = None
        if has_conditions(modifier_raw):
            modifier_base, modifier_conditions = extract_conditions(modifier_raw)
            modifier_base = get_base_input(modifier_base)[0]
        else:
            modifier_base = modifier_raw

        validate_modifier(modifier_base, base_pairs, edge_triggered_bases)

        activator_action = get_modified_action(activator_raw, action, throttle_busy, debounce_busy)
        if context_ref is not None:
            activator_action = wrap_with_context(activator_action, context_ref)

        activator_base, activator_inputs = get_base_input(activator_raw)
        for inp in activator_inputs:
            base_input_set.add(inp)

        modifier_commands.setdefault(activator_base, []).append(
            (modifier_base, modifier_conditions, activator_action)
        )

    has_mods = bool(modifier_commands)

    has_vars = bool(immediate_variable_patterns or delayed_variable_patterns)
    has_conds = bool(immediate_conditional or delayed_conditional)
    has_edge = bool(edge_triggered_bases)

    # detect_edge_triggered has already stripped the None ('else') entries.
    def _uses_mode_age(entries):
        return any(var == MODE_AGE for conditions, _ in entries for var, _, _ in conditions)

    has_mode_age = any(
        _uses_mode_age(entries)
        for entries in list(immediate_conditional.values()) + list(delayed_conditional.values())
    )

    # Modifier-side conditions ('pedal:init + pop') are evaluated against the same
    # context, so they have to arm the clock too or they never match.
    for entries in modifier_commands.values():
        for mod_name, mod_conditions, _ in entries:
            if not mod_conditions:
                continue
            if not any(var == MODE_AGE for var, _, _ in mod_conditions):
                continue
            if mod_name in edge_triggered_bases:
                raise ValueError(
                    f"""
Cannot use ':init' '{mod_name}' with an edge-triggered base.
Put ':init' on the activator side of a plain modifier instead.
"""
                )
            has_mode_age = True

    for base_key in edge_triggered_bases:
        entries = (immediate_conditional.get(base_key) or []) + (delayed_conditional.get(base_key) or [])
        if _uses_mode_age(entries):
            raise ValueError(
                f"""
'Cannot combine {base_key}'s ':init' with ':else'.
Pair ':init' with a plain unconditioned key instead.
"""
            )

    # Check if any condition uses the 'dur' variable
    has_dur = False
    for entries in list(immediate_conditional.values()) + list(delayed_conditional.values()):
        for conditions, _ in entries:
            if any(var == "dur" for var, _, _ in conditions):
                has_dur = True
                break
        if has_dur:
            break
    # Also scan raw command keys for dur conditions (catches keys before extraction)
    if not has_dur:
        for key in commands:
            if ":dur" in key:
                has_dur = True
                break
    # Also check if any action lambda takes dur as a param
    if not has_dur:
        for action in commands.values():
            if isinstance(action, tuple) and len(action) >= 2 and callable(action[1]):
                try:
                    sig = inspect.signature(action[1])
                    if "dur" in sig.parameters:
                        has_dur = True
                        break
                except (ValueError, TypeError):
                    pass

    return {
        "immediate_commands": immediate_commands,
        "delayed_commands": delayed_commands,
        "immediate_variable_patterns": immediate_variable_patterns,
        "delayed_variable_patterns": delayed_variable_patterns,
        "immediate_conditional": immediate_conditional,
        "delayed_conditional": delayed_conditional,
        "base_input_set": base_input_set,
        "base_pairs": base_pairs,
        "unique_combos": unique_combos,
        "has_variables": has_vars,
        "has_conditions": has_conds,
        "edge_triggered_bases": edge_triggered_bases,
        "edge_else_actions": edge_else_actions,
        "has_edge_triggered": has_edge,
        "modifier_commands": modifier_commands,
        "has_modifiers": has_mods,
        "has_dur": has_dur,
        "after_commands": after_commands,
        "has_after": bool(after_commands),
        "has_mode_age": has_mode_age,
    }
