"""
Parsing, validation, and categorization for input_map.
This module handles setup-time processing (cold path).
"""
import re
import inspect

# Key syntax. The parser and input_map_types() both read these.

# `pattern`: group 1 is the number; a condition's are variable, operator, number.
# `title`: a name to show, where the id is short for something.
MODIFIERS = {
    "th": {
        "title": "throttle",
        "desc": "Input can only fire once per throttle time. Useful for continuous noises that want to act as discrete noises.",
        "pattern": r"th(?:_(\d+))?",
        "unit": "ms",
        "default": 100,
    },
    "db": {
        "title": "debounce",
        "desc": "Wait this amount of time before triggering. Useful for stops on a continuous noise, to prevent start/stop cycle repeatedly triggering.",
        "pattern": r"db(?:_(\d+))?",
        "unit": "ms",
        "default": 100,
    },
    "now": {
        "desc": "Fire immediately instead of waiting out the combo window (300ms by default). Only useful if you have a combo that also starts with this noise.",
        "pattern": r"now",
    },
    "init": {
        "desc": "When changing to a new mode, fire this instead of the normal input if it falls within the init duration (300ms by default).",
        "pattern": r"init(?:_(\d+))?",
        "unit": "ms",
        "default_setting": "user.input_map_init_window",
    },
    "condition": {
        "desc": "Fire when the specific condition is met.",
        # Filled in below, from CONDITION_VARIABLES and OPERATORS
        "pattern": "",
    },
    "else": {
        "desc": "Used when you also have other conditions defined, such as power>10 or x<-0.5. Fires when the input is triggered but the other conditions are not met.",
        "pattern": r"else",
    },
}

# `source`: the handle action that provides it; `stop` is measured on a release key.
CONDITION_VARIABLES = {
    "power": {"desc": "How loud the parrot noise is.", "source": "parrot"},
    "f0": {"title": "pitch", "desc": "The parrot noise's pitch.", "source": "parrot", "experimental": True},
    "f1": {"title": "formant 1", "desc": "The parrot noise's first formant.", "source": "parrot", "experimental": True},
    "f2": {"title": "formant 2", "desc": "The parrot noise's second formant.", "source": "parrot", "experimental": True},
    "x": {"desc": "Horizontal position, e.g. gaze.", "source": "xy"},
    "y": {"desc": "Vertical position, e.g. gaze.", "source": "xy"},
    "value": {"desc": "The input's value, e.g. how far a face expression is made.", "source": "value"},
    "dur": {"title": "duration", "unit": "ms", "desc": "Fire based on how long the input was held. On a start, fire only after this amount of time has passed, otherwise it is ignored. Useful for continuous noises on start, or defining different behaviors on stop depending on how long it was held.", "source": "stop"},
}

OPERATORS = {
    ">": "greater than",
    "<": "less than",
    ">=": "at least",
    "<=": "at most",
    "==": "equal to",
    "!=": "not equal to",
}

RELEASE_SUFFIXES = {
    "_stop": "e.g. hiss_stop",
    "_up": "e.g. a pedal's left_up",
}

CONTEXT_KEYS = set(CONDITION_VARIABLES)
# Sources that stream values; an else on their inputs fires once per change
STREAM_SOURCES = {"xy", "value"}
# Variables that take whole numbers, 0 or more
WHOLE_VARIABLES = {var for var, v in CONDITION_VARIABLES.items() if v["source"] in ("parrot", "stop")}
# Longest first, so '>=' is not read as '>'
_OPS = "|".join(re.escape(op) for op in sorted(OPERATORS, key=len, reverse=True))
_VARS = "|".join(CONDITION_VARIABLES)
MODIFIERS["condition"]["pattern"] = rf"({_VARS})({_OPS})(-?\d+(?:\.\d+)?)"
CONDITION_PATTERN = re.compile(rf"^{MODIFIERS['condition']['pattern']}$")
MISFORMATTED_CONDITION_PATTERN = re.compile(rf'({_OPS})\d')
CHORD_SEPARATOR = " + "
THROTTLE_DEFAULT_MS = MODIFIERS["th"]["default"]
DEBOUNCE_DEFAULT_MS = MODIFIERS["db"]["default"]

INIT_PATTERN = re.compile(rf"^{MODIFIERS['init']['pattern']}$")
MODE_AGE = "mode_age"
DEFAULT_INIT_WINDOW_MS = 300


LEGEND_HIDDEN_MODIFIERS = re.compile(r"^(th|db|now)(_\d+)?$")


def _legend_modifier(modifier: str):
    """One ':' modifier as a legend token. Returns (variable, text)"""
    if LEGEND_HIDDEN_MODIFIERS.match(modifier):
        return (None, None)
    match = INIT_PATTERN.match(modifier)
    if match:
        window = match.group(1)
        return (None, f"init {window}" if window else "init")
    match = CONDITION_PATTERN.match(modifier)
    if match:
        return (match.group(1), f"{match.group(1)} {match.group(2)} {match.group(3)}")
    return (None, modifier.replace("_", " "))


def mode_entries(input_map: dict, mode: str = None, current=None) -> dict:
    """Entries for `mode`, else `current()`. Modal when it has a "default"
    mode or its first value is a dict; a missing mode falls back to
    default, else the first. A flat map comes back as is, without asking
    `current`."""
    first_key = next(iter(input_map), None)
    is_modal = first_key is not None and isinstance(input_map[first_key], dict)
    if "default" not in input_map and not is_modal:
        return input_map
    if mode is None and current is not None:
        mode = current()
    fallback = input_map.get("default", input_map.get(first_key, {}))
    return input_map.get(mode, fallback)


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
        base, *modifiers = input_key.split(":")
        tokens = [_legend_modifier(s) for s in modifiers]
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


def has_chord(key: str) -> bool:
    """Check if an input key uses the cross-input chord syntax ('a + b')."""
    return CHORD_SEPARATOR in key


def extract_chord(key: str) -> tuple:
    """Split 'pedal_left + pop' into ('pedal_left', 'pop').
    Returns (chord_name, activator_key)."""
    parts = key.split(CHORD_SEPARATOR, 1)
    return parts[0].strip(), parts[1].strip()


def validate_chord(name: str, base_pairs: set, edge_triggered_bases: set):
    """Ensure a chord's held input is stateful (has start/stop pair or edge-triggered conditions)."""
    if name not in base_pairs and name not in edge_triggered_bases:
        raise ValueError(
            f"\n'{name}' is not stateful, so it can't be held in a chord. "
            f"The held input needs a '_stop' or '_up' pair or if/else edge-triggered conditions.\n"
            f"Defined base_pairs: {base_pairs}\n"
            f"Defined edge_triggered_bases: {edge_triggered_bases}\n"
        )

def parse_condition(modifier: str):
    """Parse a single modifier like 'power>10' into ('power', '>', 10.0), or None
    if not a condition. ':init' and ':init_300' desugar to a mode_age condition."""
    match = INIT_PATTERN.match(modifier)
    if match:
        window = match.group(1)
        return (MODE_AGE, '<', float(window) if window else float(DEFAULT_INIT_WINDOW_MS))
    match = CONDITION_PATTERN.match(modifier)
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
    """Quick check if an input key contains condition modifiers."""
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
    in place. Returns (edge_bases set, else_actions dict).

    An input whose conditions read a stream (x, y, value) goes edge-triggered:
    its else fires once per change. Any other else fires on every event no
    condition matched, as a last entry with no conditions."""
    edge_bases = set()
    else_actions = {}
    for base_key, entries in list(conditional_dict.items()):
        remaining = []
        fallback = None
        stream = any(
            CONDITION_VARIABLES.get(var, {}).get("source") in STREAM_SOURCES
            for conditions, _ in entries if conditions
            for var, _, _ in conditions
        )
        for conditions, action_tuple in entries:
            if conditions is None:
                if stream:
                    edge_bases.add(base_key)
                    else_actions[base_key] = action_tuple
                else:
                    fallback = ([], action_tuple)
            else:
                remaining.append((conditions, action_tuple))
        if fallback:
            remaining.append(fallback)
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

def parse_modifier(modifier: str, init_window_ms: int = None) -> dict:
    """'th_90' -> {"id": "th", "text": "th_90", "value": 90, "ms": 90}
    'th' -> value None, ms the default. 'power>10' -> value ["power", ">", 10.0].
    Unknown -> id ""."""
    out = {"id": "", "text": modifier, "value": None}
    for seg_id, seg in MODIFIERS.items():
        match = re.fullmatch(seg["pattern"], modifier)
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
    base, *modifiers = text.split(":")
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
        "modifiers": [parse_modifier(s.strip(), init_window_ms) for s in modifiers],
    }

def parse_key(key: str, init_window_ms: int = None) -> dict:
    """What an input map key says, in parts.

    'pedal_left + pop pop:power>10:th_90' ->
        base "pop pop", inputs ["pop", "pop"], release_suffix "", release_of "",
        variables [], modifiers [condition, th],
        chord {the same, for "pedal_left"}

    release_suffix is the end that makes it a release key ('_stop', '_up'),
    release_of the input it releases. A bare init's ms is init_window_ms,
    else the window last set."""
    chord = None
    if has_chord(key):
        chord_raw, key_raw = extract_chord(key)
        chord = _parse_side(chord_raw, init_window_ms)
    else:
        key_raw = key
    out = _parse_side(key_raw, init_window_ms)
    out["key"] = key
    out["chord"] = chord
    # Chords are experimental; their checks run when the map loads
    out["error"] = "" if chord else _key_reason(out, _side_info(out))
    return out

def key_options(key: str) -> dict:
    """What can still go on a key, by the same checks a map loads with:
    {"modifiers": [id], "conditions": {variable: {"operators": [op], "whole": bool}}}.
    Empty for a key that can't take more: a combo, a variable key, a chord,
    or a key that is already bad. Rules across keys (else needs a condition,
    one throttle per sound) are input_map_check's."""
    out = {"modifiers": [], "conditions": {}}
    if has_chord(key) or parse_key(key)["error"]:
        return out

    def ok(candidate):
        side = _parse_side(candidate)
        return not _key_reason(side, _side_info(side), ranges=False)

    for var in CONDITION_VARIABLES:
        operators = [op for op in OPERATORS if ok(f"{key}:{var}{op}1")]
        if operators:
            out["conditions"][var] = {"operators": operators, "whole": var in WHOLE_VARIABLES}
    out["modifiers"] = [seg_id for seg_id in MODIFIERS
                       if (bool(out["conditions"]) if seg_id == "condition" else ok(f"{key}:{seg_id}"))]
    return out

def get_modified_action(input, action, throttle_busy, debounce_busy):
    # Late import to avoid circular dependency
    from .input_map import input_map_throttle, input_map_debounce

    # Keyed by the input, so every key of a sound shares one throttle.
    # validate_commands has made th start-only and db stop-only.
    base_input = get_base_input(input)[0]
    if ":th" in input:
        match = re.search(r':th_(\d+)', input)
        throttle_amount = int(match.group(1)) if match else THROTTLE_DEFAULT_MS
        return (action[0], lambda: input_map_throttle(throttle_amount, base_input, action[1], throttle_busy))
    if ":db" in input:
        match = re.search(r':db_(\d+)', input)
        debounce_amount = int(match.group(1)) if match else DEBOUNCE_DEFAULT_MS
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

_AFTER_PATTERN = re.compile(r"after(?:_\d+)?")
_VALID_MODIFIERS = "th, th_N, now, init, init_N, db_N on a stop, a condition like power>10, else"

def _report(key: str, reason: str):
    print(f"input_map: skipped '{key}'. {reason}")

def _side_info(side: dict) -> dict:
    """The parts of a key the checks read: conditions (without init), init
    window, else, throttle and debounce ms, now."""
    info = {"conditions": [], "init": None, "else": False, "th": None, "db": None, "now": False}
    for seg in side["modifiers"]:
        sid = seg["id"]
        if sid == "condition":
            info["conditions"].append(tuple(seg["value"]))
        elif sid == "init":
            info["init"] = seg["ms"]
        elif sid == "else":
            info["else"] = True
        elif sid in ("th", "db"):
            info[sid] = seg["ms"]
        elif sid == "now":
            info["now"] = True
    return info

def _range_is_empty(conditions: list) -> bool:
    """True when the conditions on some variable can never all hold."""
    bounds = {}
    for var, op, n in conditions:
        lo, lo_inc, hi, hi_inc = bounds.get(var, (float("-inf"), False, float("inf"), False))
        if op in (">", ">=", "=="):
            inc = op != ">"
            if n > lo or (n == lo and not inc):
                lo, lo_inc = n, inc
        if op in ("<", "<=", "=="):
            inc = op != "<"
            if n < hi or (n == hi and not inc):
                hi, hi_inc = n, inc
        bounds[var] = (lo, lo_inc, hi, hi_inc)
    return any(lo > hi or (lo == hi and not (lo_inc and hi_inc)) for lo, lo_inc, hi, hi_inc in bounds.values())

def _key_reason(side: dict, info: dict, ranges: bool = True) -> str:
    """Why one key can't work on its own, or ''. ranges=False skips the check
    that a variable's conditions can all hold, which depends on the numbers."""
    base = side["base"]
    modifiers = side["modifiers"]
    release = side["release_of"]
    seen = set()
    for seg in modifiers:
        sid, text = seg["id"], seg["text"]
        if not sid:
            if _AFTER_PATTERN.fullmatch(text):
                return (f"':after' was removed in 1.3.0. A plain '{base}' already waits out the combo window "
                        f"and fires only if no combo follows; use '{base}:now' to also fire right away.")
            return f"Invalid modifier :{text}. Valid modifiers are {_VALID_MODIFIERS}."
        if sid != "condition" and sid in seen:
            return f"'{sid}' appears more than once."
        seen.add(sid)
    if MISFORMATTED_CONDITION_PATTERN.search(base):
        return f"'{base}' looks like a condition without its ':'. Conditions go after the input: 'pop:power>10'."
    if modifiers and (len(side["inputs"]) > 1 or side["variables"]):
        return "Modifiers don't go on combos or variable keys. A combo uses the throttle of its sounds."
    if info["else"] and (info["conditions"] or info["init"] is not None):
        return "':else' goes on a key of its own, next to the conditioned keys."
    for seg in modifiers:
        sid, text = seg["id"], seg["text"]
        number = f"_{seg['value']}" if seg.get("value") is not None and sid in ("th", "db") else ""
        if sid == "th" and seg["ms"] == 0:
            return "A throttle of 0 does nothing. Leave it off, or give it a time."
        if sid == "th" and release:
            return (f"Throttle doesn't go on a stop: it can drop a release and leave a key held. "
                    f"To bridge gaps, debounce the stop: '{base}:db{number}'.")
        if sid == "db" and not release:
            return (f"Debounce only works on a stop, like '{base}_stop:db{number}'. "
                    f"To fire once '{base}' is held {seg['ms']}ms, use '{base}:dur>={seg['ms']}'. "
                    f"To limit repeats, use '{base}:th{number}'.")
        if sid == "now" and release:
            return "':now' only matters for combos, and a combo can't include a stop."
        if sid == "condition":
            var, op, n = seg["value"]
            if var in WHOLE_VARIABLES and ("-" in text or "." in text):
                return f"'{var}' takes whole numbers, 0 or more."
            if release and CONDITION_VARIABLES[var]["source"] == "parrot":
                return f"'{var}' only comes with a start, not a stop."
            if var == "dur" and not release and op not in (">", ">="):
                return (f"On a start, dur takes only a lower bound: '{base}:dur>=N' fires once held N ms. "
                        f"For a short press, put it on the stop: '{base}_stop:{text}'.")
    if ranges and _range_is_empty(info["conditions"]):
        return "These conditions can never all hold."
    return ""

def _kind(conditions: list) -> str:
    """'stream' for x, y, value; 'event' for everything else."""
    for var, _, _ in conditions:
        if CONDITION_VARIABLES.get(var, {}).get("source") in STREAM_SOURCES:
            return "stream"
    return "event" if conditions else ""

def _dur_lower_bound(conditions: list):
    lows = [n for var, op, n in conditions if var == "dur" and op in (">", ">=")]
    return max(lows) if lows else None

def check_commands(commands: dict, init_window_ms: int = None):
    """(the keys of a map that can work, in order; {key: why it can't} for the rest).

    A later key replaces an earlier one for the same input and conditions,
    as a spread override does ('{**base, "sh:th_100": ...}' over 'sh:th_90').
    Throttle belongs to the sound: the value on one key goes on all its keys."""
    parsed = {}
    reasons = {}
    for key, action in commands.items():
        if not key or not isinstance(action, tuple) or len(action) < 2:
            parsed[key] = None
            continue
        if has_chord(key):
            parsed[key] = None
            continue
        side = parse_key(key, init_window_ms)
        info = _side_info(side)
        reason = side["error"]
        if reason:
            reasons[key] = reason
            continue
        identity = (side["base"], frozenset(info["conditions"]), info["init"], info["else"])
        parsed[key] = (side, info, identity)

    # Later replaces earlier: keep the last key for each identity, at its place
    last = {}
    for key, entry in parsed.items():
        if entry:
            last[entry[2]] = key
    keys = [k for k, e in parsed.items() if e is None or last[e[2]] == k]

    groups = {}
    for key in keys:
        if parsed[key]:
            groups.setdefault(parsed[key][0]["base"], []).append(key)

    throttles = {}
    for base, group in groups.items():
        info = {k: parsed[k][1] for k in group}
        conditioned = [k for k in group if info[k]["conditions"] and not any(var == "dur" for var, _, _ in info[k]["conditions"])]
        elses = [k for k in group if info[k]["else"]]
        inits = [k for k in group if info[k]["init"] is not None]
        plains = [k for k in group if not info[k]["conditions"] and info[k]["init"] is None and not info[k]["else"]]
        for k in elses:
            if inits:
                reasons[k] = "':init' can't be combined with ':else' on one input. Pair ':init' with a plain key instead."
            elif not [c for c in group if info[c]["conditions"]]:
                reasons[k] = f"':else' needs a condition on the same input, like '{base}:power>10'."
            elif info[k]["th"] is not None and conditioned:
                reasons[k] = (f"Put the throttle on a conditioned key, '{conditioned[0]}:th_{info[k]['th']}'. "
                              f"It covers the else too.")
        # A plain key is the fallback for conditioned keys; else is another
        for k in plains:
            if elses and k not in reasons:
                reasons[k] = f"'{base}' and '{elses[0]}' are both fallbacks, so only one could fire. Keep one."
        if conditioned:
            kinds = [_kind(info[k]["conditions"]) for k in conditioned]
            for k, kind in zip(conditioned, kinds):
                if kind != kinds[0]:
                    reasons[k] = "Parrot conditions (power, f0, f1, f2) and position conditions (x, y, value) can't share an input."
        first = None
        for k in group:
            ms = info[k]["th"]
            if k in reasons or ms is None:
                continue
            if first is None:
                first = (k, ms)
            elif ms != first[1]:
                reasons[k] = (f"'{base}' already has a throttle of {first[1]}ms on '{first[0]}'. "
                              f"A throttle belongs to the sound, so use one value.")
        if first:
            throttles[base] = first[1]

    # A dur start rules out a dur stop shorter than it
    for base, group in groups.items():
        side = parsed[group[0]][0]
        if not side["release_of"] or side["release_of"] not in groups:
            continue
        lows = [_dur_lower_bound(parsed[k][1]["conditions"]) for k in groups[side["release_of"]]]
        lows = [n for n in lows if n is not None]
        if not lows:
            continue
        floor = min(lows)
        for k in group:
            if k in reasons:
                continue
            conditions = [c for c in parsed[k][1]["conditions"] if c[0] == "dur"]
            if conditions and _range_is_empty(conditions + [("dur", ">=", floor)]):
                reasons[k] = f"'{side['release_of']}' only starts once held {floor}ms, so this stop can never match."

    out = {}
    for key in keys:
        if key in reasons:
            continue
        entry = parsed[key]
        if entry is None:
            out[key] = commands[key]
            continue
        side, info, _ = entry
        ms = throttles.get(side["base"])
        is_hold = _dur_lower_bound(info["conditions"]) is not None and not side["release_of"]
        if ms is not None and info["th"] is None and not is_hold:
            out[f"{key}:th_{ms}"] = commands[key]
        else:
            out[key] = commands[key]
    return out, reasons

def validate_commands(commands: dict, init_window_ms: int = None) -> dict:
    """The keys that can work. Each one that can't is printed with the reason;
    the rest still load."""
    out, reasons = check_commands(commands, init_window_ms)
    for key, reason in reasons.items():
        _report(key, reason)
    return out

def _release_base(base_combo: str) -> str:
    """'hiss' for 'hiss_stop' or 'hiss_up', else ''."""
    for suffix in RELEASE_SUFFIXES:
        if base_combo.endswith(suffix) and len(base_combo) > len(suffix):
            return base_combo[:-len(suffix)]
    return ""

def categorize_commands(commands, throttle_busy, debounce_busy, context_ref=None, hold_gate=None):
    """hold_gate(base, fn): wraps a debounced stop of a 'dur>=N' start, so the
    hold ends when the stop does and the stop fires only if a stage did."""
    commands = validate_commands(commands)

    # Inputs with 'dur>=N' starts: each N is a stage, fired while held
    hold_stages = {}
    hold_bases = set()
    for input in commands:
        if has_chord(input) or has_variables(input) or not has_conditions(input):
            continue
        cleaned_key, conditions = extract_conditions(input)
        base_combo = get_base_input(cleaned_key)[0]
        if conditions and " " not in base_combo and not _release_base(base_combo) \
                and any(var == "dur" for var, _, _ in conditions):
            hold_bases.add(base_combo)
    hold_stop_debounced = set()

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
    chord_input_keys = []

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

        if has_chord(input):
            chord_input_keys.append((input, action))
            continue

        if has_variables(input):
            if not validate_variable_action(input, action):
                print(f"Warning: Variable pattern '{input}' has mismatched lambda signature")
                continue
            variable_commands.append((input, action))
        elif has_conditions(input):
            cleaned_key, conditions = extract_conditions(input)
            base_combo, base_inputs = get_base_input(cleaned_key)

            if base_combo in hold_bases:
                lower = [int(n if op == ">=" else n + 1) for var, op, n in conditions if var == "dur"]
                others = [c for c in conditions if c[0] != "dur"]
                if context_ref is not None:
                    action = wrap_with_context(action, context_ref)
                hold_stages.setdefault(base_combo, []).append((max(lower), others, action))
                base_input_set.add(base_combo)
                base_pairs.add(base_combo)
                continue

            release_of = _release_base(base_combo)
            if hold_gate and release_of in hold_bases and ":db" in cleaned_key:
                hold_stop_debounced.add(release_of)
                if context_ref is not None:
                    action = wrap_with_context(action, context_ref)
                action = (action[0], hold_gate(release_of, action[1]))

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
            base_combo, base_inputs = get_base_input(input)

            release_of = _release_base(base_combo)
            if hold_gate and release_of in hold_bases and ":db" in input:
                hold_stop_debounced.add(release_of)
                if context_ref is not None:
                    action = wrap_with_context(action, context_ref)
                action = (action[0], hold_gate(release_of, action[1]))

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

    # Process deferred chord keys (e.g. "pedal_left + pop", "gaze:x<500 + pop")
    chord_commands = {}
    for raw_key, action in chord_input_keys:
        chord_raw, activator_raw = extract_chord(raw_key)

        # Parse optional conditions from held side (e.g. "gaze:x<500" → "gaze", conditions)
        chord_conditions = None
        if has_conditions(chord_raw):
            chord_base, chord_conditions = extract_conditions(chord_raw)
            chord_base = get_base_input(chord_base)[0]
        else:
            chord_base = chord_raw

        try:
            validate_chord(chord_base, base_pairs, edge_triggered_bases)
        except ValueError as e:
            _report(raw_key, str(e).strip())
            continue
        # Region matching can't hold mode_age, so ':init' never matches there
        if chord_conditions and chord_base in edge_triggered_bases \
                and any(var == MODE_AGE for var, _, _ in chord_conditions):
            _report(raw_key, f"Cannot use ':init' on '{chord_base}', an edge-triggered base. "
                             f"Put ':init' on the activator side of a plain chord instead.")
            continue

        activator_action = get_modified_action(activator_raw, action, throttle_busy, debounce_busy)
        if context_ref is not None:
            activator_action = wrap_with_context(activator_action, context_ref)

        activator_base, activator_inputs = get_base_input(activator_raw)
        for inp in activator_inputs:
            base_input_set.add(inp)

        chord_commands.setdefault(activator_base, []).append(
            (chord_base, chord_conditions, activator_action)
        )

    has_mods = bool(chord_commands)

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

    # Held-side conditions ('pedal:init + pop') are evaluated against the same
    # context, so they have to arm the clock too or they never match.
    for entries in chord_commands.values():
        for mod_name, mod_conditions, _ in entries:
            if mod_conditions and any(var == MODE_AGE for var, _, _ in mod_conditions):
                has_mode_age = True

    # A stop follows the start that fired: an init start's stop is the init
    # stop, whenever the release comes. Keyed by the paired input.
    init_starts = {}
    init_stops = set()
    for base_key, entries in list(immediate_conditional.items()) + list(delayed_conditional.items()):
        windows = [n for conditions, _ in entries for var, _, n in conditions if var == MODE_AGE]
        if not windows:
            continue
        release_of = _release_base(base_key)
        if release_of:
            init_stops.add(release_of)
        elif base_key in base_pairs:
            init_starts[base_key] = max(windows)

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
        "chord_commands": chord_commands,
        "has_chords": has_mods,
        "has_dur": has_dur or bool(hold_stages),
        "has_mode_age": has_mode_age,
        "hold_stages": {base: sorted(stages, key=lambda s: s[0]) for base, stages in hold_stages.items()},
        "hold_stop_debounced": hold_stop_debounced,
        "init_starts": init_starts,
        "init_stops": init_stops,
        "release_of": {f"{base}{suffix}": base for base in base_pairs for suffix in RELEASE_SUFFIXES},
    }
