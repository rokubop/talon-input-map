from talon import actions
from .input_map import InputMap, input_map_saved, input_map_mode_revert
from .input_map_parse import (
    get_base_input,
    extract_variables,
    pattern_to_regex,
    match_variable_pattern,
    has_variables,
    has_conditions,
    has_modifier,
    extract_modifier,
    validate_modifier,
    validate_variable_action,
    parse_condition,
    extract_conditions,
    evaluate_conditions,
    build_legend,
    parse_key,
    parse_segment,
    CONTEXT_KEYS,
)
from .input_map_channel import (
    channel_register,
    channel_unregister,
    channel_list,
    channel_get,
    channel_handle,
    channel_mode_set,
    channel_mode_get,
    channel_mode_cycle,
    channel_mode_revert,
    channel_get_legend,
    channel_event_register,
    channel_event_unregister,
    _channels,
    _channel_callbacks,
)
from .input_map_single import (
    normalize_single_map,
    single_handle,
    single_mode_set,
    single_mode_get,
    single_mode_cycle,
    single_mode_revert,
    single_get_legend,
    _singles,
    _singles_map_ref,
    _singles_mode_order,
)
import contextlib
import io

def _load(config):
    """Set up a map. Returns it and what setup printed, where bad keys are reported."""
    printed = io.StringIO()
    with contextlib.redirect_stdout(printed):
        input_map = InputMap()
        input_map.setup(config)
    return input_map, printed.getvalue()

def _assert_clean(printed):
    assert printed == "", f"Failed: expected no errors, got:\n{printed}"

def _assert_bad(printed, key, *hints):
    """The error names the key and says each hint (a reason, or the key to write instead)."""
    assert key in printed, f"Failed: no error naming '{key}', got:\n{printed}"
    for hint in hints:
        assert hint in printed, f"Failed: error for '{key}' doesn't say '{hint}', got:\n{printed}"

# To run the test suite, open the Talon REPL and run:
#
# ```python
# actions.user.input_map_test()
# ```

def test_get_base_input():
    print("Testing get_base_input...")

    # Test single input
    base, inputs = get_base_input("pop")
    assert base == "pop" and inputs == ["pop"], f"Failed: got {base}, {inputs}"
    print("  ✓ Single input")

    # Test combo
    base, inputs = get_base_input("pop cluck")
    assert base == "pop cluck" and inputs == ["pop", "cluck"], f"Failed: got {base}, {inputs}"
    print("  ✓ Combo input")

    # Test with modifier
    base, inputs = get_base_input("pop:th_100")
    assert base == "pop" and inputs == ["pop"], f"Failed: got {base}, {inputs}"
    print("  ✓ Input with modifier")

    print()

def test_has_variables():
    print("Testing has_variables...")

    assert has_variables("tut $noise") == True
    print("  ✓ Pattern with variable")

    assert has_variables("pop cluck") == False
    print("  ✓ Pattern without variable")

    print()

def test_extract_variables():
    print("Testing extract_variables...")

    vars = extract_variables("tut $noise")
    assert vars == ["noise"], f"Failed: got {vars}"
    print("  ✓ Single variable")

    vars = extract_variables("$a $b $c")
    assert vars == ["a", "b", "c"], f"Failed: got {vars}"
    print("  ✓ Multiple variables")

    vars = extract_variables("pop cluck")
    assert vars == [], f"Failed: got {vars}"
    print("  ✓ No variables")

    print()

def test_pattern_to_regex():
    print("Testing pattern_to_regex...")

    regex = pattern_to_regex("tut $noise")
    assert regex == r"tut\ (\w+)", f"Failed: got {regex}"
    print("  ✓ Variable pattern to regex")

    print()

def test_match_variable_pattern():
    print("Testing match_variable_pattern...")

    # Should match
    result = match_variable_pattern("tut pop", "tut $noise")
    assert result == {"noise": "pop"}, f"Failed: got {result}"
    print("  ✓ Match single variable")

    # Should not match
    result = match_variable_pattern("pop cluck", "tut $noise")
    assert result is None, f"Failed: got {result}"
    print("  ✓ No match for different pattern")

    print()

def test_validate_variable_action():
    print("Testing validate_variable_action...")

    # Valid: lambda with matching params
    valid = validate_variable_action("tut $noise", ("cmd", lambda noise: None))
    assert valid == True, f"Failed: got {valid}"
    print("  ✓ Lambda with matching params")

    # Valid: lambda with no params
    valid = validate_variable_action("tut $noise", ("cmd", lambda: None))
    assert valid == True, f"Failed: got {valid}"
    print("  ✓ Lambda with no params")

    # Invalid: not callable
    valid = validate_variable_action("tut $noise", ("cmd", None))
    assert valid == False, f"Failed: got {valid}"
    print("  ✓ Not callable returns False")

    print()

def test_input_map_single_command():
    print("Testing InputMap single command...")

    executed = []
    test_config = {
        "pop": ("action A", lambda: executed.append("A")),
        "cluck": ("action B", lambda: executed.append("B")),
    }

    input_map = InputMap()
    input_map.setup(test_config)

    input_map.execute("pop")
    assert executed == ["A"], f"Failed: got {executed}"
    print("  ✓ Single command executes")

    input_map.execute("cluck")
    assert executed == ["A", "B"], f"Failed: got {executed}"
    print("  ✓ Multiple single commands execute")

    print()

def test_input_map_combo():
    print("Testing InputMap combo...")

    executed = []
    test_config = {
        "pop": ("action A", lambda: executed.append("A")),
        "pop cluck": ("combo AB", lambda: executed.append("AB")),
    }

    input_map = InputMap()
    input_map.setup(test_config)

    # Single should be delayed, not immediate
    input_map.execute("pop")
    assert executed == [], f"Failed: executed too early, got {executed}"
    print("  ✓ First input in combo is delayed")

    print()

def test_input_map_immediate_combo():
    print("Testing InputMap immediate combo (no longer combos exist)...")

    executed = []
    test_config = {
        "pop": ("action A", lambda: executed.append("A")),
        "cluck": ("action B", lambda: executed.append("B")),
    }

    input_map = InputMap()
    input_map.setup(test_config)

    # Should execute immediately since there's no "pop X" combo
    input_map.execute("pop")
    assert executed == ["A"], f"Failed: got {executed}"
    print("  ✓ Command with no combo executes immediately")

    print()

def test_input_map_variable_pattern():
    print("Testing InputMap variable patterns...")

    executed = []
    test_config = {
        "pop": ("base pop", lambda: executed.append("pop")),
        "tut": ("base tut", lambda: executed.append("tut")),
        "tut $noise": ("variable action", lambda noise: executed.append(f"noise_{noise}")),
    }

    input_map = InputMap()
    input_map.setup(test_config)

    # Execute tut, then pop - should match "tut $noise" pattern
    executed.clear()
    input_map.execute("tut")
    input_map.execute("pop")
    assert "noise_pop" in executed, f"Failed: got {executed}"
    print("  ✓ Variable pattern matches and executes")

    print()

def test_input_map_modes():
    print("Testing InputMap mode switching...")

    executed = []
    test_config = {
        "default": {
            "pop": ("default action", lambda: executed.append("default")),
        },
        "fighting": {
            "pop": ("fighting action", lambda: executed.append("fighting")),
        }
    }

    input_map = InputMap()
    input_map.setup(test_config)

    # Should start in default mode
    input_map.execute("pop")
    assert executed == ["default"], f"Failed: got {executed}"
    print("  ✓ Starts in default mode")

    # Switch to fighting mode
    input_map.setup_mode("fighting")
    executed.clear()
    input_map.execute("pop")
    assert executed == ["fighting"], f"Failed: got {executed}"
    print("  ✓ Mode switching works")

    print()

def test_input_map_now_modifier():
    print("Testing InputMap :now modifier...")

    executed = []
    test_config = {
        "pop:now": ("immediate", lambda: executed.append("immediate")),
        "pop cluck": ("combo", lambda: executed.append("combo")),
    }

    input_map = InputMap()
    input_map.setup(test_config)

    input_map.execute("pop")
    # Should execute immediately due to :now but still track for combo
    assert executed == ["immediate"], f"Failed: got {executed}"
    print("  ✓ :now modifier executes immediately")

    # Now test that combo still works
    input_map.execute("cluck")
    assert "combo" in executed, f"Failed: combo didn't execute, got {executed}"
    assert executed == ["immediate", "combo"], f"Failed: unexpected execution order, got {executed}"
    print("  ✓ Combo still executes after :now")

    print()

def test_input_map_continuous_pairs():
    print("Testing InputMap continuous input pairs...")

    executed = []
    test_config = {
        "hiss": ("start", lambda: executed.append("start")),
        "hiss_stop": ("stop", lambda: executed.append("stop")),
    }

    input_map = InputMap()
    input_map.setup(test_config)

    input_map.execute("hiss")
    assert "start" in executed, f"Failed: got {executed}"
    print("  ✓ Continuous input start")

    executed.clear()
    input_map.execute("hiss_stop")
    assert "stop" in executed, f"Failed: got {executed}"
    print("  ✓ Continuous input stop")

    print()

def test_input_map_throttle():
    print("Testing InputMap throttle modifier...")

    executed = []
    test_config = {
        "pop:th_100": ("throttled action", lambda: executed.append("throttled")),
    }

    input_map = InputMap()
    input_map.setup(test_config)

    # First execution should work
    input_map.execute("pop")
    assert executed == ["throttled"], f"Failed: got {executed}"
    print("  ✓ First throttled command executes")

    # Immediate second execution should be blocked
    input_map.execute("pop")
    assert executed == ["throttled"], f"Failed: second execution wasn't blocked, got {executed}"
    print("  ✓ Second immediate execution is throttled")

    # After throttle period, should execute again
    actions.sleep("110ms")
    input_map.execute("pop")
    assert executed == ["throttled", "throttled"], f"Failed: didn't execute after throttle period, got {executed}"
    print("  ✓ Executes again after throttle period")

    print()

def test_input_map_debounce():
    print("Testing InputMap debounce modifier...")

    executed = []
    test_config = {
        "hiss": ("start", lambda: executed.append("start")),
        "hiss_stop:db_100": ("debounced stop", lambda: executed.append("stop")),
    }

    input_map = InputMap()
    input_map.setup(test_config)

    input_map.execute("hiss")
    input_map.execute("hiss_stop")
    assert executed == ["start"], f"Failed: debounced stop executed immediately, got {executed}"
    print("  ✓ Debounced stop doesn't execute immediately")

    actions.sleep("200ms")
    assert executed == ["start", "stop"], f"Failed: didn't execute after debounce period, got {executed}"
    print("  ✓ Executes after debounce period")

    print()

def test_channel_register_unregister():
    print("Testing channel register/unregister...")

    # Clean up any existing test channel
    if "test_channel" in _channels:
        channel_unregister("test_channel")

    test_config = {
        "pop": ("action A", lambda: None),
    }

    # Register
    channel_register("test_channel", test_config)
    assert "test_channel" in channel_list(), f"Failed: channel not in list"
    print("  ✓ Channel registered and appears in list")

    # Unregister
    channel_unregister("test_channel")
    assert "test_channel" not in channel_list(), f"Failed: channel still in list"
    print("  ✓ Channel unregistered")

    print()

def test_channel_re_registration():
    print("Testing channel re-registration warning...")

    # Clean up
    if "test_reregister" in _channels:
        channel_unregister("test_reregister")

    executed = []
    config1 = {"pop": ("first", lambda: executed.append("first"))}
    config2 = {"pop": ("second", lambda: executed.append("second"))}

    channel_register("test_reregister", config1)
    channel_register("test_reregister", config2)  # Should warn and keep first

    # Execute and verify first config is kept
    channel_handle("test_reregister", "pop")
    assert executed == ["first"], f"Failed: got {executed}"
    print("  ✓ Re-registration keeps original channel")

    channel_unregister("test_reregister")
    print()

def test_channel_get():
    print("Testing channel_get...")

    if "test_get" in _channels:
        channel_unregister("test_get")

    test_config = {
        "default": {"pop": ("default action", lambda: None)},
        "combat": {"pop": ("combat action", lambda: None)},
    }

    channel_register("test_get", test_config)

    # Get full config
    full = channel_get("test_get")
    assert "default" in full and "combat" in full, f"Failed: got {full}"
    print("  ✓ Get full config")

    # Get specific mode
    combat = channel_get("test_get", "combat")
    assert "pop" in combat, f"Failed: got {combat}"
    print("  ✓ Get specific mode")

    channel_unregister("test_get")
    print()

def test_channel_handle():
    print("Testing channel_handle...")

    if "test_handle" in _channels:
        channel_unregister("test_handle")

    executed = []
    test_config = {
        "pop": ("action A", lambda: executed.append("A")),
        "cluck": ("action B", lambda: executed.append("B")),
    }

    channel_register("test_handle", test_config)

    channel_handle("test_handle", "pop")
    assert executed == ["A"], f"Failed: got {executed}"
    print("  ✓ Channel handle executes action")

    channel_handle("test_handle", "cluck")
    assert executed == ["A", "B"], f"Failed: got {executed}"
    print("  ✓ Channel handle executes multiple actions")

    channel_unregister("test_handle")
    print()

def test_channel_modes():
    print("Testing channel mode switching...")

    if "test_modes" in _channels:
        channel_unregister("test_modes")

    executed = []
    test_config = {
        "default": {"pop": ("default", lambda: executed.append("default"))},
        "combat": {"pop": ("combat", lambda: executed.append("combat"))},
    }

    channel_register("test_modes", test_config)

    # Should start in default
    assert channel_mode_get("test_modes") == "default", f"Failed: not in default mode"
    print("  ✓ Starts in default mode")

    channel_handle("test_modes", "pop")
    assert executed == ["default"], f"Failed: got {executed}"
    print("  ✓ Executes default mode action")

    # Switch to combat
    channel_mode_set("test_modes", "combat")
    assert channel_mode_get("test_modes") == "combat", f"Failed: not in combat mode"
    print("  ✓ Mode set works")

    executed.clear()
    channel_handle("test_modes", "pop")
    assert executed == ["combat"], f"Failed: got {executed}"
    print("  ✓ Executes combat mode action")

    # Cycle back to default
    next_mode = channel_mode_cycle("test_modes")
    assert next_mode == "default", f"Failed: got {next_mode}"
    print("  ✓ Mode cycle works")

    channel_unregister("test_modes")
    print()

def test_channel_get_legend():
    print("Testing channel_get_legend...")

    if "test_legend" in _channels:
        channel_unregister("test_legend")

    test_config = {
        "default": {
            "pop": ("Click", lambda: None),
            "hiss:th_100": ("Scroll", lambda: None),
            "cluck": ("", lambda: None),  # Empty label, should be filtered
        },
    }

    channel_register("test_legend", test_config)

    legend = channel_get_legend("test_legend")
    assert legend == {
        "pop": "Click",
        "hiss": "Scroll",
    }, f"Failed: got {legend}"
    print("  ✓ Legend generated correctly (modifier hidden, empty label filtered)")

    channel_unregister("test_legend")
    print()

def test_channel_events():
    print("Testing channel events...")

    if "test_events" in _channels:
        channel_unregister("test_events")

    events = []
    def on_input(event):
        events.append((event.input, event.label))

    test_config = {
        "pop": ("Click", lambda: None),
    }

    channel_register("test_events", test_config)
    channel_event_register("test_events", on_input)

    channel_handle("test_events", "pop")
    assert len(events) == 1, f"Failed: event not triggered, got {events}"
    assert events[0] == ("pop", "Click"), f"Failed: wrong event data, got {events}"
    print("  ✓ Event callback triggered")

    # Unregister and verify no more events
    channel_event_unregister("test_events", on_input)
    events.clear()
    channel_handle("test_events", "pop")
    assert len(events) == 0, f"Failed: event still triggered after unregister, got {events}"
    print("  ✓ Event callback unregistered")

    channel_unregister("test_events")
    print()

def test_parse_condition():
    print("Testing parse_condition...")

    result = parse_condition("power>10")
    assert result == ("power", ">", 10.0), f"Failed: got {result}"
    print("  ✓ power>10")

    result = parse_condition("x<=500.5")
    assert result == ("x", "<=", 500.5), f"Failed: got {result}"
    print("  ✓ x<=500.5")

    result = parse_condition("value==1")
    assert result == ("value", "==", 1.0), f"Failed: got {result}"
    print("  ✓ value==1")

    result = parse_condition("f0!=0")
    assert result == ("f0", "!=", 0.0), f"Failed: got {result}"
    print("  ✓ f0!=0")

    result = parse_condition("power>-5")
    assert result == ("power", ">", -5.0), f"Failed: got {result}"
    print("  ✓ negative threshold")

    # Non-condition segments
    result = parse_condition("th_100")
    assert result is None, f"Failed: got {result}"
    print("  ✓ th_100 returns None")

    result = parse_condition("db_100")
    assert result is None, f"Failed: got {result}"
    print("  ✓ db_100 returns None")

    result = parse_condition("pop")
    assert result is None, f"Failed: got {result}"
    print("  ✓ pop returns None")

    print()

def test_extract_conditions():
    print("Testing extract_conditions...")

    cleaned, conds = extract_conditions("pop:power>10")
    assert cleaned == "pop", f"Failed cleaned: got {cleaned}"
    assert conds == [("power", ">", 10.0)], f"Failed conds: got {conds}"
    print("  ✓ pop:power>10")

    cleaned, conds = extract_conditions("pop:power>10:db_100")
    assert cleaned == "pop:db_100", f"Failed cleaned: got {cleaned}"
    assert conds == [("power", ">", 10.0)], f"Failed conds: got {conds}"
    print("  ✓ pop:power>10:db_100 preserves modifier")

    cleaned, conds = extract_conditions("gaze:x<500:y<500")
    assert cleaned == "gaze", f"Failed cleaned: got {cleaned}"
    assert len(conds) == 2, f"Failed: expected 2 conditions, got {len(conds)}"
    print("  ✓ multiple conditions")

    cleaned, conds = extract_conditions("pop:th_100")
    assert cleaned == "pop:th_100", f"Failed cleaned: got {cleaned}"
    assert conds == [], f"Failed conds: got {conds}"
    print("  ✓ no conditions returns empty list")

    print()

def test_evaluate_conditions():
    print("Testing evaluate_conditions...")

    ctx = {"power": 15.0, "f0": 100.0, "f1": 200.0, "f2": 300.0, "x": 400.0, "y": 300.0, "value": 1.0}

    assert evaluate_conditions([("power", ">", 10.0)], ctx) == True
    print("  ✓ power>10 with power=15")

    assert evaluate_conditions([("power", ">", 20.0)], ctx) == False
    print("  ✓ power>20 with power=15 fails")

    assert evaluate_conditions([("power", "<=", 15.0)], ctx) == True
    print("  ✓ power<=15 with power=15")

    assert evaluate_conditions([("x", "<", 500.0), ("y", "<", 500.0)], ctx) == True
    print("  ✓ multiple conditions AND (both true)")

    assert evaluate_conditions([("x", "<", 500.0), ("y", "<", 100.0)], ctx) == False
    print("  ✓ multiple conditions AND (one false)")

    # None context value
    ctx_none = {"power": None, "f0": None, "f1": None, "f2": None, "x": None, "y": None, "value": None}
    assert evaluate_conditions([("power", ">", 10.0)], ctx_none) == False
    print("  ✓ None context value returns False")

    assert evaluate_conditions([], ctx) == True
    print("  ✓ empty conditions returns True")

    print()

def test_input_map_conditional_basic():
    print("Testing InputMap conditional basic...")

    executed = []
    test_config = {
        "pop:power>10": ("loud pop", lambda: executed.append("loud")),
        "pop:power<=10": ("soft pop", lambda: executed.append("soft")),
    }

    input_map = InputMap()
    input_map.setup(test_config)

    input_map.execute("pop", power=15.0)
    assert executed == ["loud"], f"Failed: got {executed}"
    print("  ✓ power>10 matches loud")

    executed.clear()
    input_map.execute("pop", power=5.0)
    assert executed == ["soft"], f"Failed: got {executed}"
    print("  ✓ power<=10 matches soft")

    print()

def test_input_map_conditional_no_match():
    print("Testing InputMap conditional no match...")

    executed = []
    test_config = {
        "pop:power>100": ("very loud", lambda: executed.append("very_loud")),
    }

    input_map = InputMap()
    input_map.setup(test_config)

    input_map.execute("pop", power=5.0)
    assert executed == [], f"Failed: should not have executed, got {executed}"
    print("  ✓ no condition matches, silent no-op")

    print()

def test_input_map_conditional_with_fallback():
    print("Testing InputMap conditional with fallback...")

    executed = []
    test_config = {
        "pop:power>10": ("loud pop", lambda: executed.append("loud")),
        "pop:else": ("default pop", lambda: executed.append("default")),
    }

    input_map = InputMap()
    input_map.setup(test_config)

    # High power should match conditional
    input_map.execute("pop", power=15.0)
    assert executed == ["loud"], f"Failed: got {executed}"
    print("  ✓ conditional matches when condition is true")

    # Low power should fall through to else
    executed.clear()
    input_map.execute("pop", power=5.0)
    assert executed == ["default"], f"Failed: got {executed}"
    print("  ✓ falls through to else")

    print()

def test_input_map_conditional_missing_context():
    print("Testing InputMap conditional missing context...")

    executed = []
    test_config = {
        "pop:power>10": ("loud pop", lambda: executed.append("loud")),
        "pop:else": ("default pop", lambda: executed.append("default")),
    }

    input_map = InputMap()
    input_map.setup(test_config)

    # No power provided (None) should fall through to else
    input_map.execute("pop")
    assert executed == ["default"], f"Failed: got {executed}"
    print("  ✓ power=None falls through to else")

    print()

def test_input_map_conditional_multi_condition():
    print("Testing InputMap conditional multi-condition...")

    executed = []
    test_config = {
        "gaze:x<500:y<500": ("top-left", lambda: executed.append("top_left")),
        "gaze:else": ("default gaze", lambda: executed.append("default")),
    }

    input_map = InputMap()
    input_map.setup(test_config)

    input_map.execute("gaze", x=100.0, y=100.0)
    assert executed == ["top_left"], f"Failed: got {executed}"
    print("  ✓ x<500 AND y<500 matches")

    executed.clear()
    input_map.execute("gaze", x=600.0, y=100.0)
    assert executed == ["default"], f"Failed: got {executed}"
    print("  ✓ x>=500 falls through to else")

    print()

def test_input_map_context_params_basic():
    print("Testing InputMap context params basic...")

    executed = []
    test_config = {
        "pop": ("power pop", lambda power: executed.append(f"power={power}")),
    }

    input_map = InputMap()
    input_map.setup(test_config)

    input_map.execute("pop", power=42.0)
    assert executed == ["power=42.0"], f"Failed: got {executed}"
    print("  ✓ Single context param (power) passed to lambda")

    print()

def test_input_map_context_params_multi():
    print("Testing InputMap context params multi...")

    executed = []
    test_config = {
        "gaze": ("aim", lambda x, y: executed.append(f"x={x},y={y}")),
    }

    input_map = InputMap()
    input_map.setup(test_config)

    input_map.execute("gaze", x=100.0, y=200.0)
    assert executed == ["x=100.0,y=200.0"], f"Failed: got {executed}"
    print("  ✓ Multiple context params (x, y) passed to lambda")

    print()

def test_input_map_context_params_zero_arg():
    print("Testing InputMap context params zero-arg regression...")

    executed = []
    test_config = {
        "pop": ("click", lambda: executed.append("clicked")),
    }

    input_map = InputMap()
    input_map.setup(test_config)

    input_map.execute("pop", power=42.0)
    assert executed == ["clicked"], f"Failed: got {executed}"
    print("  ✓ Zero-arg lambda still works unchanged")

    print()

def test_input_map_context_params_variable_excluded():
    print("Testing InputMap context params variable excluded...")

    executed = []
    test_config = {
        "tut $noise": ("variable action", lambda noise: executed.append(f"noise={noise}")),
        "tut": ("base tut", lambda: executed.append("tut")),
        "pop": ("base pop", lambda: executed.append("pop")),
    }

    input_map = InputMap()
    input_map.setup(test_config)

    # Variable pattern should NOT be wrapped - "noise" is a captured input name, not a context key
    input_map.execute("tut")
    input_map.execute("pop")
    assert "noise=pop" in executed, f"Failed: got {executed}"
    print("  ✓ Variable pattern lambda not wrapped (params are captured inputs)")

    print()

def test_input_map_context_params_conditional():
    print("Testing InputMap context params with conditional...")

    executed = []
    test_config = {
        "pop:power>10": ("loud", lambda power: executed.append(f"loud={power}")),
        "pop:power<=10": ("soft", lambda power: executed.append(f"soft={power}")),
    }

    input_map = InputMap()
    input_map.setup(test_config)

    input_map.execute("pop", power=15.0)
    assert executed == ["loud=15.0"], f"Failed: got {executed}"
    print("  ✓ Conditional + context param works (loud)")

    executed.clear()
    input_map.execute("pop", power=5.0)
    assert executed == ["soft=5.0"], f"Failed: got {executed}"
    print("  ✓ Conditional + context param works (soft)")

    print()

def test_input_map_context_params_throttle():
    print("Testing InputMap context params with throttle...")

    executed = []
    test_config = {
        "pop:th_100": ("throttled", lambda power: executed.append(f"power={power}")),
    }

    input_map = InputMap()
    input_map.setup(test_config)

    input_map.execute("pop", power=42.0)
    assert executed == ["power=42.0"], f"Failed: got {executed}"
    print("  ✓ First throttled call with context param executes")

    input_map.execute("pop", power=99.0)
    assert executed == ["power=42.0"], f"Failed: second call wasn't throttled, got {executed}"
    print("  ✓ Second immediate call is throttled")

    actions.sleep("110ms")
    input_map.execute("pop", power=77.0)
    assert executed == ["power=42.0", "power=77.0"], f"Failed: got {executed}"
    print("  ✓ Executes again after throttle with updated context")

    print()

def test_has_conditions_else():
    print("Testing has_conditions with else...")

    assert has_conditions("gaze:else") == True
    print("  ✓ gaze:else returns True")

    assert has_conditions("gaze:else:db_100") == True
    print("  ✓ gaze:else:db_100 returns True")

    assert has_conditions("pop") == False
    print("  ✓ pop without else or condition returns False")

    print()

def test_extract_conditions_else():
    print("Testing extract_conditions with else...")

    cleaned, conds = extract_conditions("gaze:else")
    assert cleaned == "gaze", f"Failed cleaned: got {cleaned}"
    assert conds is None, f"Failed conds: expected None, got {conds}"
    print("  ✓ gaze:else returns None conditions")

    cleaned, conds = extract_conditions("gaze:else:db_100")
    assert cleaned == "gaze:db_100", f"Failed cleaned: got {cleaned}"
    assert conds is None, f"Failed conds: expected None, got {conds}"
    print("  ✓ gaze:else:db_100 preserves modifier, returns None conditions")

    cleaned, conds = extract_conditions("pop:power>10")
    assert conds == [("power", ">", 10.0)], f"Failed: non-else still works, got {conds}"
    print("  ✓ non-else conditions unchanged")

    print()

def test_input_map_edge_triggered_basic():
    print("Testing InputMap edge-triggered basic...")

    executed = []
    test_config = {
        "gaze:x<500":  ("look left", lambda: executed.append("left")),
        "gaze:x>=500": ("look right", lambda: executed.append("right")),
        "gaze:else":   ("neutral", lambda: executed.append("neutral")),
    }

    input_map = InputMap()
    input_map.setup(test_config)

    # Enter left region
    input_map.execute("gaze", x=100.0)
    assert executed == ["left"], f"Failed: got {executed}"
    print("  ✓ First entry into left region fires")

    # Same region - should suppress
    input_map.execute("gaze", x=200.0)
    assert executed == ["left"], f"Failed: should suppress, got {executed}"
    print("  ✓ Same region suppressed")

    # Transition to right region
    input_map.execute("gaze", x=600.0)
    assert executed == ["left", "right"], f"Failed: got {executed}"
    print("  ✓ Transition to right fires")

    # Same right region - suppress
    input_map.execute("gaze", x=700.0)
    assert executed == ["left", "right"], f"Failed: should suppress, got {executed}"
    print("  ✓ Same right region suppressed")

    print()

def test_input_map_edge_triggered_else_fires():
    print("Testing InputMap edge-triggered else fires...")

    executed = []
    test_config = {
        "gaze:x<500":  ("look left", lambda: executed.append("left")),
        "gaze:else":   ("neutral", lambda: executed.append("neutral")),
    }

    input_map = InputMap()
    input_map.setup(test_config)

    # Enter left
    input_map.execute("gaze", x=100.0)
    assert executed == ["left"], f"Failed: got {executed}"
    print("  ✓ Enter left region fires")

    # Leave left (no condition matches) - else fires
    input_map.execute("gaze", x=600.0)
    assert executed == ["left", "neutral"], f"Failed: got {executed}"
    print("  ✓ Else fires on leaving region")

    # Stay in else - suppress
    input_map.execute("gaze", x=700.0)
    assert executed == ["left", "neutral"], f"Failed: should suppress, got {executed}"
    print("  ✓ Else suppressed on repeat")

    print()

def test_input_map_edge_triggered_with_context_params():
    print("Testing InputMap edge-triggered with context params...")

    executed = []
    test_config = {
        "gaze:x<500":  ("look left", lambda x, y: executed.append(f"left x={x} y={y}")),
        "gaze:x>=500": ("look right", lambda x, y: executed.append(f"right x={x} y={y}")),
        "gaze:else":   ("neutral", lambda: executed.append("neutral")),
    }

    input_map = InputMap()
    input_map.setup(test_config)

    input_map.execute("gaze", x=100.0, y=200.0)
    assert executed == ["left x=100.0 y=200.0"], f"Failed: got {executed}"
    print("  ✓ Context params passed in edge-triggered mode")

    input_map.execute("gaze", x=600.0, y=300.0)
    assert executed == ["left x=100.0 y=200.0", "right x=600.0 y=300.0"], f"Failed: got {executed}"
    print("  ✓ Context params updated on region transition")

    print()

def test_input_map_edge_triggered_mode_reset():
    print("Testing InputMap edge-triggered mode reset...")

    executed = []
    test_config = {
        "default": {
            "gaze:x<500":  ("look left", lambda: executed.append("left")),
            "gaze:x>=500": ("look right", lambda: executed.append("right")),
            "gaze:else":   ("neutral", lambda: executed.append("neutral")),
        },
        "other": {
            "gaze:x<500":  ("look left 2", lambda: executed.append("left2")),
            "gaze:x>=500": ("look right 2", lambda: executed.append("right2")),
            "gaze:else":   ("neutral 2", lambda: executed.append("neutral2")),
        }
    }

    input_map = InputMap()
    input_map.setup(test_config)

    # Enter left region
    input_map.execute("gaze", x=100.0)
    assert executed == ["left"], f"Failed: got {executed}"

    # Switch mode - should reset active region
    input_map.setup_mode("other")
    executed.clear()

    # Same x=100 should fire again because region state was reset
    input_map.execute("gaze", x=100.0)
    assert executed == ["left2"], f"Failed: got {executed}"
    print("  ✓ Mode switch resets active region state")

    print()

def test_input_map_no_else_unchanged():
    print("Testing InputMap no else unchanged (regression)...")

    executed = []
    test_config = {
        "pop:power>10": ("loud pop", lambda: executed.append("loud")),
        "pop:power<=10": ("soft pop", lambda: executed.append("soft")),
    }

    input_map = InputMap()
    input_map.setup(test_config)

    # Without else, should fire every time (per-event filter mode)
    input_map.execute("pop", power=15.0)
    assert executed == ["loud"], f"Failed: got {executed}"

    input_map.execute("pop", power=15.0)
    assert executed == ["loud", "loud"], f"Failed: should fire again, got {executed}"
    print("  ✓ Without else, fires every event (per-event filter mode)")

    input_map.execute("pop", power=5.0)
    assert executed == ["loud", "loud", "soft"], f"Failed: got {executed}"
    print("  ✓ Condition change also fires")

    print()

def test_input_map_edge_triggered_negative_threshold():
    print("Testing InputMap edge-triggered with negative thresholds...")

    executed = []
    test_config = {
        "gaze:x<-0.5":  ("look left", lambda: executed.append("left")),
        "gaze:x>0.5":   ("look right", lambda: executed.append("right")),
        "gaze:else":     ("neutral", lambda: executed.append("neutral")),
    }

    input_map = InputMap()
    input_map.setup(test_config)

    # Dead zone - else fires
    input_map.execute("gaze", x=0.0)
    assert executed == ["neutral"], f"Failed: got {executed}"
    print("  ✓ Dead zone fires else")

    # Enter left region (negative threshold)
    input_map.execute("gaze", x=-0.8)
    assert executed == ["neutral", "left"], f"Failed: got {executed}"
    print("  ✓ Negative threshold x<-0.5 fires")

    # Stay in left - suppress
    input_map.execute("gaze", x=-0.9)
    assert executed == ["neutral", "left"], f"Failed: should suppress, got {executed}"
    print("  ✓ Same negative region suppressed")

    # Back to dead zone
    input_map.execute("gaze", x=0.1)
    assert executed == ["neutral", "left", "neutral"], f"Failed: got {executed}"
    print("  ✓ Return to dead zone fires else")

    # Enter right region
    input_map.execute("gaze", x=0.8)
    assert executed == ["neutral", "left", "neutral", "right"], f"Failed: got {executed}"
    print("  ✓ Positive threshold x>0.5 fires")

    print()

def test_input_map_spread_override_same_modifier():
    print("Testing InputMap spread override with same modifier...")

    executed = []
    default_input_map = {
        "pop": ("default pop", lambda: executed.append("default_pop")),
        "hiss:th_90": ("default scroll", lambda: executed.append("default_scroll")),
        "hiss_stop": ("stop", lambda: executed.append("stop")),
    }

    combat_input_map = {
        **default_input_map,
        "hiss:th_90": ("combat scroll", lambda: executed.append("combat_scroll")),
    }

    input_map = InputMap()
    input_map.setup(combat_input_map)

    # Override should win
    input_map.execute("hiss")
    assert executed == ["combat_scroll"], f"Failed: got {executed}"
    print("  ✓ Same modifier override wins")

    # Inherited command still works
    executed.clear()
    input_map.execute("pop")
    assert executed == ["default_pop"], f"Failed: got {executed}"
    print("  ✓ Inherited command unchanged")

    print()

def test_input_map_spread_override_different_modifier():
    print("Testing InputMap spread override with different modifier...")

    executed = []
    default_input_map = {
        "pop": ("default pop", lambda: executed.append("default_pop")),
        "hiss:th_90": ("throttled scroll", lambda: executed.append("throttled")),
        "hiss_stop": ("stop", lambda: executed.append("stop")),
    }

    combat_input_map = {
        **default_input_map,
        "hiss:th_300": ("slow scroll", lambda: executed.append("slow")),
    }

    input_map = InputMap()
    input_map.setup(combat_input_map)

    # Both keys exist in the dict ("hiss:th_90" from spread, "hiss:th_300" from override)
    # Both resolve to base "hiss" - the later one replaces the earlier
    input_map.execute("hiss")
    assert executed == ["slow"], f"Failed: override should win, got {executed}"
    print("  ✓ Later key (th_300) replaces spread key (th_90)")

    actions.sleep("150ms")
    input_map.execute("hiss")
    assert executed == ["slow"], f"Failed: th_300 should still hold at 150ms, got {executed}"
    print("  ✓ Override's throttle applies")

    print()

def test_input_map_spread_override_modes():
    print("Testing InputMap spread override with modes...")

    executed = []
    default_input_map = {
        "hiss:th_90": ("default scroll", lambda: executed.append("default_scroll")),
        "hiss_stop": ("stop", lambda: executed.append("stop")),
    }

    combat_input_map = {
        **default_input_map,
        "hiss:th_90": ("combat scroll", lambda: executed.append("combat_scroll")),
    }

    test_config = {
        "default": default_input_map,
        "combat": combat_input_map,
    }

    input_map = InputMap()
    input_map.setup(test_config)

    # Default mode uses default scroll
    input_map.execute("hiss")
    assert executed == ["default_scroll"], f"Failed: got {executed}"
    print("  ✓ Default mode uses default action")

    # Wait for throttle to expire before switching modes
    actions.sleep("100ms")

    # Switch to combat mode - override should be active
    input_map.setup_mode("combat")
    executed.clear()
    input_map.execute("hiss")
    assert executed == ["combat_scroll"], f"Failed: got {executed}"
    print("  ✓ Combat mode uses overridden action")

    # Wait for throttle to expire before switching back
    actions.sleep("100ms")

    # Switch back to default - should use default again
    input_map.setup_mode("default")
    executed.clear()
    input_map.execute("hiss")
    assert executed == ["default_scroll"], f"Failed: got {executed}"
    print("  ✓ Switching back restores default action")

    print()

def _cleanup_single(name: str):
    """Clean up a single registration for testing."""
    _singles.pop(name, None)
    _singles_map_ref.pop(name, None)
    _singles_mode_order.pop(name, None)

def test_normalize_single_map_simple():
    print("Testing normalize_single_map simple...")

    result = normalize_single_map("pop", {
        "click": lambda: None,
        "repeat": lambda: None,
    })
    assert "click" in result and "repeat" in result
    assert "pop" in result["click"]
    assert result["click"]["pop"][0] == ""
    assert callable(result["click"]["pop"][1])
    print("  ✓ Callable values wrapped correctly")

    print()

def test_normalize_single_map_tuple():
    print("Testing normalize_single_map tuple...")

    result = normalize_single_map("pop", {
        "click": ("left click", lambda: None),
        "repeat": ("repeat", lambda: None),
    })
    assert "click" in result and "repeat" in result
    assert "pop" in result["click"]
    assert result["click"]["pop"][0] == "left click"
    print("  ✓ Tuple values preserved correctly")

    print()

def test_normalize_single_map_expanded():
    print("Testing normalize_single_map expanded...")

    inner = {
        "pop":     ("click", lambda: None),
        "pop pop": ("double click", lambda: None),
    }
    result = normalize_single_map("pop", {
        "click": inner,
    })
    assert result["click"] is inner
    print("  ✓ Dict values pass through as-is")

    print()

def test_single_handle_basic():
    print("Testing single_handle basic...")

    _cleanup_single("test_pop")

    executed = []
    pop_map = {
        "click": lambda: executed.append("click"),
        "repeat": lambda: executed.append("repeat"),
    }

    single_handle("test_pop", pop_map)
    assert executed == ["click"], f"Failed: got {executed}"
    print("  ✓ Executes first mode action")

    _cleanup_single("test_pop")
    print()

def test_single_handle_tuple():
    print("Testing single_handle tuple...")

    _cleanup_single("test_pop_tuple")

    executed = []
    pop_map = {
        "click": ("left click", lambda: executed.append("click")),
        "repeat": ("repeat", lambda: executed.append("repeat")),
    }

    single_handle("test_pop_tuple", pop_map)
    assert executed == ["click"], f"Failed: got {executed}"
    print("  ✓ Tuple form executes correctly")

    _cleanup_single("test_pop_tuple")
    print()

def test_single_handle_expanded():
    print("Testing single_handle expanded...")

    _cleanup_single("test_pop_exp")

    executed = []
    pop_map = {
        "click": {
            "test_pop_exp": ("click", lambda: executed.append("click")),
            "test_pop_exp test_pop_exp": ("double click", lambda: executed.append("double")),
        },
        "scroll": {
            "test_pop_exp": ("scroll", lambda: executed.append("scroll")),
        },
    }

    # Single input is delayed because of combo
    single_handle("test_pop_exp", pop_map)
    assert executed == [], f"Failed: should be delayed, got {executed}"
    print("  ✓ Single input delayed (combo exists)")

    # After combo window, single fires
    actions.sleep("310ms")
    assert executed == ["click"], f"Failed: got {executed}"
    print("  ✓ Single fires after combo window")

    # Double input triggers combo
    executed.clear()
    single_handle("test_pop_exp", pop_map)
    single_handle("test_pop_exp", pop_map)
    assert executed == ["double"], f"Failed: got {executed}"
    print("  ✓ Combo fires immediately")

    # Mode switching works
    single_mode_set("test_pop_exp", "scroll")
    executed.clear()
    single_handle("test_pop_exp", pop_map)
    assert executed == ["scroll"], f"Failed: got {executed}"
    print("  ✓ Expanded dict mode switching works")

    _cleanup_single("test_pop_exp")
    print()

def test_single_mode_switching():
    print("Testing single mode switching...")

    _cleanup_single("test_mode_switch")

    executed = []
    pop_map = {
        "click": lambda: executed.append("click"),
        "repeat": lambda: executed.append("repeat"),
    }

    single_handle("test_mode_switch", pop_map)
    assert executed == ["click"], f"Failed: got {executed}"

    single_mode_set("test_mode_switch", "repeat")
    executed.clear()
    single_handle("test_mode_switch", pop_map)
    assert executed == ["repeat"], f"Failed: got {executed}"
    print("  ✓ Mode switching changes behavior")

    _cleanup_single("test_mode_switch")
    print()

def test_single_mode_cycle():
    print("Testing single mode cycle...")

    _cleanup_single("test_cycle")

    executed = []
    pop_map = {
        "click": lambda: executed.append("click"),
        "repeat": lambda: executed.append("repeat"),
        "scroll": lambda: executed.append("scroll"),
    }

    single_handle("test_cycle", pop_map)
    assert single_mode_get("test_cycle") == "click"

    next_mode = single_mode_cycle("test_cycle")
    assert next_mode == "repeat", f"Failed: got {next_mode}"

    next_mode = single_mode_cycle("test_cycle")
    assert next_mode == "scroll", f"Failed: got {next_mode}"

    # Wrap around
    next_mode = single_mode_cycle("test_cycle")
    assert next_mode == "click", f"Failed: got {next_mode}"
    print("  ✓ Cycling with wrap-around works")

    _cleanup_single("test_cycle")
    print()

def test_single_mode_get():
    print("Testing single_mode_get...")

    _cleanup_single("test_get_mode")

    pop_map = {
        "click": lambda: None,
        "repeat": lambda: None,
    }

    single_handle("test_get_mode", pop_map)
    assert single_mode_get("test_get_mode") == "click", f"Failed: got {single_mode_get('test_get_mode')}"
    print("  ✓ Correct mode returned")

    _cleanup_single("test_get_mode")
    print()

def test_single_first_mode_is_default():
    print("Testing single first mode is default...")

    _cleanup_single("test_first_mode")

    pop_map = {
        "special": lambda: None,
        "normal": lambda: None,
    }

    single_handle("test_first_mode", pop_map)
    assert single_mode_get("test_first_mode") == "special", f"Failed: got {single_mode_get('test_first_mode')}"
    print("  ✓ First key is initial mode")

    _cleanup_single("test_first_mode")
    print()

def test_single_get_legend():
    print("Testing single_get_legend...")

    _cleanup_single("test_legend_s")

    pop_map = {
        "click": ("left click", lambda: None),
        "repeat": ("repeat cmd", lambda: None),
    }

    legend = single_get_legend("test_legend_s", pop_map)
    assert legend == {"test legend s": "left click"}, f"Failed: got {legend}"
    print("  ✓ Returns {input: label}")

    legend2 = single_get_legend("test_legend_s", pop_map, "repeat")
    assert legend2 == {"test legend s": "repeat cmd"}, f"Failed: got {legend2}"
    print("  ✓ Specific mode legend works")

    _cleanup_single("test_legend_s")
    print()

def test_single_independent_state():
    print("Testing single independent state...")

    _cleanup_single("test_ind_a")
    _cleanup_single("test_ind_b")

    executed = []
    map_a = {
        "mode1": lambda: executed.append("a_mode1"),
        "mode2": lambda: executed.append("a_mode2"),
    }
    map_b = {
        "modeX": lambda: executed.append("b_modeX"),
        "modeY": lambda: executed.append("b_modeY"),
    }

    single_handle("test_ind_a", map_a)
    single_handle("test_ind_b", map_b)
    assert executed == ["a_mode1", "b_modeX"], f"Failed: got {executed}"

    # Change mode of A, B should be unaffected
    single_mode_set("test_ind_a", "mode2")
    executed.clear()
    single_handle("test_ind_a", map_a)
    single_handle("test_ind_b", map_b)
    assert executed == ["a_mode2", "b_modeX"], f"Failed: got {executed}"
    print("  ✓ Two names don't interfere")

    _cleanup_single("test_ind_a")
    _cleanup_single("test_ind_b")
    print()

def test_single_auto_reregister():
    print("Testing single auto re-register...")

    _cleanup_single("test_rereg")

    executed = []
    map_v1 = {
        "click": lambda: executed.append("v1"),
    }
    map_v2 = {
        "click": lambda: executed.append("v2"),
    }

    single_handle("test_rereg", map_v1)
    assert executed == ["v1"], f"Failed: got {executed}"

    # New dict ref should trigger re-registration
    executed.clear()
    single_handle("test_rereg", map_v2)
    assert executed == ["v2"], f"Failed: got {executed}"
    print("  ✓ New dict ref triggers re-setup")

    _cleanup_single("test_rereg")
    print()

def test_single_mode_revert():
    print("Testing single_mode_revert...")

    _cleanup_single("test_revert_s")

    executed = []
    pop_map = {
        "click": lambda: executed.append("click"),
        "repeat": lambda: executed.append("repeat"),
    }

    single_handle("test_revert_s", pop_map)
    assert single_mode_get("test_revert_s") == "click"

    single_mode_set("test_revert_s", "repeat")
    assert single_mode_get("test_revert_s") == "repeat"

    result = single_mode_revert("test_revert_s")
    assert result == "click", f"Failed: got {result}"
    assert single_mode_get("test_revert_s") == "click"
    print("  ✓ Reverts to previous mode")

    _cleanup_single("test_revert_s")
    print()

def test_mode_revert():
    print("Testing main input_map mode_revert...")

    executed = []
    test_config = {
        "default": {
            "pop": ("default action", lambda: executed.append("default")),
        },
        "combat": {
            "pop": ("combat action", lambda: executed.append("combat")),
        }
    }

    input_map = InputMap()
    input_map.setup(test_config)

    assert input_map.current_mode == "default"
    input_map.setup_mode("combat")
    assert input_map.current_mode == "combat"
    assert input_map.previous_mode == "default"

    input_map.setup_mode(input_map.previous_mode)
    assert input_map.current_mode == "default"
    print("  ✓ Reverts to previous mode")

    print()

def test_channel_mode_revert():
    print("Testing channel_mode_revert...")

    if "test_revert_p" in _channels:
        channel_unregister("test_revert_p")

    test_config = {
        "default": {"pop": ("default", lambda: None)},
        "combat": {"pop": ("combat", lambda: None)},
    }

    channel_register("test_revert_p", test_config)

    assert channel_mode_get("test_revert_p") == "default"
    channel_mode_set("test_revert_p", "combat")
    assert channel_mode_get("test_revert_p") == "combat"

    result = channel_mode_revert("test_revert_p")
    assert result == "default", f"Failed: got {result}"
    assert channel_mode_get("test_revert_p") == "default"
    print("  ✓ Reverts channel to previous mode")

    channel_unregister("test_revert_p")
    print()

def test_handle_bool_basic():
    print("Testing handle_bool basic...")

    executed = []
    test_config = {
        "hiss": ("scroll", lambda: executed.append("start")),
        "hiss_stop": ("stop", lambda: executed.append("stop")),
    }

    input_map = InputMap()
    input_map.setup(test_config)

    input_map.execute("hiss")
    assert executed == ["start"], f"Failed: got {executed}"
    print("  ✓ active=True maps to name")

    input_map.execute("hiss_stop")
    assert executed == ["start", "stop"], f"Failed: got {executed}"
    print("  ✓ active=False maps to name_stop")

    print()

def test_handle_bool_channel():
    print("Testing handle_bool channel...")

    if "test_bool_p" in _channels:
        channel_unregister("test_bool_p")

    executed = []
    test_config = {
        "hiss": ("scroll", lambda: executed.append("start")),
        "hiss_stop": ("stop", lambda: executed.append("stop")),
    }

    channel_register("test_bool_p", test_config)

    channel_handle("test_bool_p", "hiss")
    assert executed == ["start"], f"Failed: got {executed}"

    channel_handle("test_bool_p", "hiss_stop")
    assert executed == ["start", "stop"], f"Failed: got {executed}"
    print("  ✓ Channel bool active/stop works")

    channel_unregister("test_bool_p")
    print()

def test_handle_bool_single():
    print("Testing handle_bool single...")

    _cleanup_single("test_bool_s")
    _cleanup_single("test_bool_s_stop")

    executed = []
    hiss_map = {
        "default": {
            "test_bool_s": ("scroll", lambda: executed.append("start")),
            "test_bool_s_stop": ("stop", lambda: executed.append("stop")),
        },
    }

    single_handle("test_bool_s", hiss_map)
    assert executed == ["start"], f"Failed: got {executed}"

    single_handle("test_bool_s_stop", hiss_map)
    assert executed == ["start", "stop"], f"Failed: got {executed}"
    print("  ✓ Single bool active/stop works")

    _cleanup_single("test_bool_s")
    _cleanup_single("test_bool_s_stop")
    print()

def test_has_modifier():
    print("Testing has_modifier...")

    assert has_modifier("pedal_left + pop") == True
    print("  ✓ 'pedal_left + pop' detected")

    assert has_modifier("pop") == False
    print("  ✓ 'pop' not a modifier")

    assert has_modifier("pop cluck") == False
    print("  ✓ 'pop cluck' not a modifier")

    assert has_modifier("pedal_left + pop cluck") == True
    print("  ✓ 'pedal_left + pop cluck' detected")

    print()

def test_extract_modifier():
    print("Testing extract_modifier...")

    mod, act = extract_modifier("pedal_left + pop")
    assert mod == "pedal_left" and act == "pop", f"Failed: got {mod}, {act}"
    print("  ✓ Simple modifier split")

    mod, act = extract_modifier("pedal_left + pop cluck")
    assert mod == "pedal_left" and act == "pop cluck", f"Failed: got {mod}, {act}"
    print("  ✓ Modifier with combo activator")

    print()

def test_validate_modifier():
    print("Testing validate_modifier...")

    # Valid: in base_pairs
    try:
        validate_modifier("pedal_left", {"pedal_left"}, set())
        print("  ✓ Valid modifier in base_pairs")
    except ValueError:
        assert False, "Should not raise for valid modifier"

    # Valid: in edge_triggered_bases
    try:
        validate_modifier("gaze", set(), {"gaze"})
        print("  ✓ Valid modifier in edge_triggered_bases")
    except ValueError:
        assert False, "Should not raise for valid edge modifier"

    # Invalid: not stateful
    try:
        validate_modifier("pop", set(), set())
        assert False, "Should have raised ValueError"
    except ValueError:
        print("  ✓ Invalid modifier raises ValueError")

    print()

def test_modifier_held_basic():
    print("Testing modifier held basic (start/stop)...")

    executed = []
    test_config = {
        "pedal_left":       ("hold",    lambda: executed.append("hold")),
        "pedal_left_stop":  ("release", lambda: executed.append("release")),
        "pop":              ("click",   lambda: executed.append("click")),
        "pedal_left + pop": ("mod click", lambda: executed.append("mod_click")),
    }

    input_map = InputMap()
    input_map.setup(test_config)

    # Pop without pedal held → normal action
    input_map.execute("pop")
    assert executed == ["click"], f"Failed: got {executed}"
    print("  ✓ Pop without modifier → normal")

    # Hold pedal, then pop → modifier action
    executed.clear()
    input_map.execute("pedal_left")
    input_map.execute("pop")
    assert "mod_click" in executed, f"Failed: got {executed}"
    print("  ✓ Pop while pedal held → modifier action")

    # Release pedal, then pop → normal action
    executed.clear()
    input_map.execute("pedal_left_stop")
    input_map.execute("pop")
    assert executed == ["release", "click"], f"Failed: got {executed}"
    print("  ✓ Pop after release → normal action")

    print()

def test_modifier_edge_triggered():
    print("Testing modifier with edge-triggered conditions...")

    executed = []
    test_config = {
        "gaze:x<500":      ("look left", lambda: executed.append("left")),
        "gaze:x>=500":     ("look right", lambda: executed.append("right")),
        "gaze:else":        ("neutral", lambda: executed.append("neutral")),
        "pop":              ("click",   lambda: executed.append("click")),
        "gaze + pop":       ("gaze click", lambda: executed.append("gaze_click")),
    }

    input_map = InputMap()
    input_map.setup(test_config)

    # Pop in neutral (else) → normal
    input_map.execute("pop")
    assert executed == ["click"], f"Failed: got {executed}"
    print("  ✓ Pop in neutral → normal")

    # Enter left region, then pop → modifier
    executed.clear()
    input_map.execute("gaze", x=100.0)
    input_map.execute("pop")
    assert "gaze_click" in executed, f"Failed: got {executed}"
    print("  ✓ Pop while gaze active → modifier action")

    # Enter else region, then pop → normal
    executed.clear()
    input_map.execute("gaze", x=600.0)  # goes to right
    input_map.execute("pop")
    # gaze is in right region (not else), so modifier is active
    assert "gaze_click" in executed, f"Failed: got {executed}"
    print("  ✓ Pop while gaze in non-else region → modifier action")

    print()

def test_modifier_release_resets_held():
    print("Testing modifier release resets held state...")

    executed = []
    test_config = {
        "pedal_left":       ("hold",    lambda: executed.append("hold")),
        "pedal_left_stop":  ("release", lambda: executed.append("release")),
        "pop":              ("click",   lambda: executed.append("click")),
        "pedal_left + pop": ("mod click", lambda: executed.append("mod_click")),
    }

    input_map = InputMap()
    input_map.setup(test_config)

    # Hold → pop (modifier) → release → pop (normal)
    input_map.execute("pedal_left")
    input_map.execute("pop")
    assert "mod_click" in executed, f"Failed first: got {executed}"

    executed.clear()
    input_map.execute("pedal_left_stop")
    input_map.execute("pop")
    assert executed == ["release", "click"], f"Failed second: got {executed}"
    print("  ✓ Hold → mod_click → release → normal click")

    print()

def test_modifier_with_combo_activator():
    print("Testing modifier with combo activator...")

    executed = []
    test_config = {
        "pedal_left":              ("hold",    lambda: executed.append("hold")),
        "pedal_left_stop":         ("release", lambda: executed.append("release")),
        "pop":                     ("click",   lambda: executed.append("click")),
        "pop cluck":               ("combo",   lambda: executed.append("combo")),
        "pedal_left + pop cluck":  ("mod combo", lambda: executed.append("mod_combo")),
    }

    input_map = InputMap()
    input_map.setup(test_config)

    # Hold pedal, then pop cluck → modifier combo
    input_map.execute("pedal_left")
    executed.clear()
    input_map.execute("pop")
    input_map.execute("cluck")
    assert "mod_combo" in executed, f"Failed: got {executed}"
    print("  ✓ Modifier with combo activator works")

    print()

def test_modifier_mode_switch_resets():
    print("Testing modifier mode switch resets held state...")

    executed = []
    test_config = {
        "default": {
            "pedal_left":       ("hold",    lambda: executed.append("hold")),
            "pedal_left_stop":  ("release", lambda: executed.append("release")),
            "pop":              ("click",   lambda: executed.append("click")),
            "pedal_left + pop": ("mod click", lambda: executed.append("mod_click")),
        },
        "other": {
            "pop":              ("other click", lambda: executed.append("other_click")),
        },
    }

    input_map = InputMap()
    input_map.setup(test_config)

    # Hold pedal in default mode
    input_map.execute("pedal_left")

    # Switch mode - should reset held state
    input_map.setup_mode("other")
    executed.clear()

    input_map.execute("pop")
    assert executed == ["other_click"], f"Failed: got {executed}"
    print("  ✓ Mode switch resets _held_inputs")

    print()

def test_modifier_has_modifiers_false():
    print("Testing has_modifiers=False when no + keys...")

    test_config = {
        "pop":  ("click",   lambda: None),
        "hiss": ("scroll",  lambda: None),
    }

    input_map = InputMap()
    input_map.setup(test_config)

    assert input_map.has_modifiers == False, f"Failed: has_modifiers should be False"
    assert input_map._held_inputs == {}, f"Failed: _held_inputs should be empty"
    print("  ✓ has_modifiers=False, zero overhead path")

    print()

def test_modifier_fallthrough():
    print("Testing modifier fallthrough...")

    executed = []
    test_config = {
        "pedal_left":       ("hold",    lambda: executed.append("hold")),
        "pedal_left_stop":  ("release", lambda: executed.append("release")),
        "pop":              ("click",   lambda: executed.append("click")),
        "pedal_left + pop": ("mod click", lambda: executed.append("mod_click")),
    }

    input_map = InputMap()
    input_map.setup(test_config)

    # Without holding pedal, pop should fall through to normal
    input_map.execute("pop")
    assert executed == ["click"], f"Failed: got {executed}"
    print("  ✓ Modifier not active → falls through to normal dispatch")

    print()

def test_modifier_conditional():
    print("Testing modifier with conditions on modifier side...")

    executed = []
    test_config = {
        "gaze:x<500":       ("look left", lambda: executed.append("left")),
        "gaze:x>=500":      ("look right", lambda: executed.append("right")),
        "gaze:else":         ("neutral", lambda: executed.append("neutral")),
        "pop":               ("click",   lambda: executed.append("click")),
        "gaze:x<500 + pop":  ("left click", lambda: executed.append("left_click")),
        "gaze:x>=500 + pop": ("right click", lambda: executed.append("right_click")),
    }

    input_map = InputMap()
    input_map.setup(test_config)

    # Pop in neutral → normal
    input_map.execute("pop")
    assert executed == ["click"], f"Failed: got {executed}"
    print("  ✓ Pop in neutral → normal click")

    # Enter left region, then pop → left modifier
    executed.clear()
    input_map.execute("gaze", x=100.0)
    input_map.execute("pop")
    assert "left_click" in executed, f"Failed: got {executed}"
    print("  ✓ Pop while gaze x<500 → left_click")

    # Enter right region, then pop → right modifier
    executed.clear()
    input_map.execute("gaze", x=600.0)
    input_map.execute("pop")
    assert "right_click" in executed, f"Failed: got {executed}"
    print("  ✓ Pop while gaze x>=500 → right_click")

    # Back to else, then pop → normal
    executed.clear()
    input_map.execute("gaze")  # no x → else
    input_map.execute("pop")
    assert executed == ["neutral", "click"], f"Failed: got {executed}"
    print("  ✓ Pop while gaze in else → normal click")

    print()

def test_modifier_parse_validation_error():
    print("Testing modifier parse validation error...")

    executed = []
    test_config = {
        "pop":              ("click",   lambda: executed.append("click")),
        "pop + cluck":      ("mod click", lambda: None),
        "cluck":            ("cluck",   lambda: executed.append("cluck")),
    }

    input_map, printed = _load(test_config)
    _assert_bad(printed, "pop + cluck", "not stateful")
    print("  ✓ Non-stateful modifier prints an error")

    input_map.execute("cluck")
    assert executed == ["cluck"], f"Failed: rest of the map should work, got {executed}"
    print("  ✓ The rest of the map still loads")

    print()

def test_edge_debounce_delays_transition():
    print("Testing edge debounce delays transition...")

    executed = []
    test_config = {
        "gaze:x<500":  ("look left", lambda: executed.append("left")),
        "gaze:x>=500": ("look right", lambda: executed.append("right")),
        "gaze:else":   ("neutral", lambda: executed.append("neutral")),
    }

    input_map = InputMap()
    input_map.setup(test_config)
    input_map.edge_debounce_ms = 50

    # Enter left region - should be delayed
    input_map.execute("gaze", x=100.0)
    assert executed == [], f"Failed: should be delayed, got {executed}"
    print("  ✓ Transition delayed")

    # After debounce, should fire
    actions.sleep("100ms")
    assert executed == ["left"], f"Failed: got {executed}"
    print("  ✓ Fires after debounce window")

    print()

def test_edge_debounce_flicker_settles():
    print("Testing edge debounce flicker settles...")

    executed = []
    test_config = {
        "gaze:x<500":  ("look left", lambda: executed.append("left")),
        "gaze:x>=500": ("look right", lambda: executed.append("right")),
        "gaze:else":   ("neutral", lambda: executed.append("neutral")),
    }

    input_map = InputMap()
    input_map.setup(test_config)
    input_map.edge_debounce_ms = 50

    # Rapid flicker: left → right → left (within debounce window)
    input_map.execute("gaze", x=100.0)
    input_map.execute("gaze", x=600.0)
    input_map.execute("gaze", x=200.0)
    assert executed == [], f"Failed: should all be delayed, got {executed}"

    actions.sleep("60ms")
    # Should settle to the last value (left, since x=200 < 500)
    assert executed == ["left"], f"Failed: should settle to left, got {executed}"
    print("  ✓ Flicker settles to final state")

    print()

def test_edge_debounce_active_region_stable():
    print("Testing edge debounce active_region stable during window...")

    executed = []
    test_config = {
        "gaze:x<500":  ("look left", lambda: executed.append("left")),
        "gaze:x>=500": ("look right", lambda: executed.append("right")),
        "gaze:else":   ("neutral", lambda: executed.append("neutral")),
    }

    input_map = InputMap()
    input_map.setup(test_config)
    input_map.edge_debounce_ms = 50

    # First, establish a region without debounce to set baseline
    input_map.edge_debounce_ms = 0
    input_map.execute("gaze", x=100.0)
    assert executed == ["left"], f"Setup failed: got {executed}"
    assert input_map._active_region.get("gaze") == 0  # left region index

    # Now enable debounce and trigger transition
    input_map.edge_debounce_ms = 50
    executed.clear()
    input_map.execute("gaze", x=600.0)

    # During debounce window, _active_region should still be old value
    assert input_map._active_region.get("gaze") == 0, f"Failed: region changed during debounce"
    print("  ✓ _active_region retains old value during debounce")

    actions.sleep("60ms")
    assert input_map._active_region.get("gaze") == 1, f"Failed: region not updated after debounce"
    print("  ✓ _active_region updated after debounce resolves")

    print()

def test_edge_debounce_zero_unchanged():
    print("Testing edge debounce ms=0 unchanged behavior...")

    executed = []
    test_config = {
        "gaze:x<500":  ("look left", lambda: executed.append("left")),
        "gaze:x>=500": ("look right", lambda: executed.append("right")),
        "gaze:else":   ("neutral", lambda: executed.append("neutral")),
    }

    input_map = InputMap()
    input_map.setup(test_config)
    # edge_debounce_ms defaults to 0

    input_map.execute("gaze", x=100.0)
    assert executed == ["left"], f"Failed: got {executed}"
    print("  ✓ Immediate transition with debounce=0")

    input_map.execute("gaze", x=600.0)
    assert executed == ["left", "right"], f"Failed: got {executed}"
    print("  ✓ Second transition immediate with debounce=0")

    print()

def test_edge_debounce_mode_switch_cancels():
    print("Testing edge debounce mode switch cancels pending jobs...")

    executed = []
    test_config = {
        "default": {
            "gaze:x<500":  ("look left", lambda: executed.append("left")),
            "gaze:x>=500": ("look right", lambda: executed.append("right")),
            "gaze:else":   ("neutral", lambda: executed.append("neutral")),
        },
        "other": {
            "pop": ("click", lambda: executed.append("click")),
        },
    }

    input_map = InputMap()
    input_map.setup(test_config)
    input_map.edge_debounce_ms = 50

    # Trigger a debounced transition
    input_map.execute("gaze", x=100.0)
    assert executed == [], f"Failed: should be delayed, got {executed}"

    # Switch mode - should cancel pending debounce jobs
    input_map.setup_mode("other")

    actions.sleep("60ms")
    assert executed == [], f"Failed: debounce should have been cancelled, got {executed}"
    print("  ✓ Mode switch cancels pending debounce jobs")

    print()

def test_legend_multiple_cases():
    print("Testing legend keeps each case for a shared base...")

    legend = build_legend({
        "pop": ("click", lambda: None),
        "hiss:th_100": ("scroll", lambda: None),
        "hiss_stop": ("stop", lambda: None),
        "left_up:dur<300": ("tap", lambda: None),
        "left_up:dur>=300": ("hold", lambda: None),
        "cluck": ("", lambda: None),
    })

    assert legend == {
        "pop": "click",
        "hiss": "scroll",
        "hiss stop": "stop",
        "left up < 300": "tap",
        "left up >= 300": "hold",
    }, f"Failed: got {legend}"
    print("  ✓ dur cases get their own rows, lone bases stay bare")

    print()

def test_dur_up_creates_base_pairs():
    print("Testing dur _up creates base_pairs...")

    from .input_map_parse import categorize_commands

    test_config = {
        "left": ("press", lambda: None),
        "left_up": ("release", lambda: None),
    }

    result = categorize_commands(test_config, {}, {})
    assert "left" in result["base_pairs"], f"Failed: _up suffix should create base pair, got {result['base_pairs']}"
    print("  ✓ _up suffix triggers base_pairs detection")

    print()

def test_dur_basic_up():
    print("Testing dur basic _up (tap vs hold)...")

    import time

    executed = []
    test_config = {
        "left": ("press", lambda: None),
        "left_up:dur<300": ("tap", lambda: executed.append("tap")),
        "left_up:dur>=300": ("hold", lambda: executed.append("hold")),
    }

    input_map = InputMap()
    input_map.setup(test_config)

    # Tap: quick press and release
    input_map.execute("left")
    actions.sleep("50ms")
    input_map.execute("left_up")
    assert executed == ["tap"], f"Failed: expected tap, got {executed}"
    print("  ✓ Quick tap (dur<300) detected")

    # Hold: long press and release
    executed.clear()
    input_map.execute("left")
    actions.sleep("350ms")
    input_map.execute("left_up")
    assert executed == ["hold"], f"Failed: expected hold, got {executed}"
    print("  ✓ Long hold (dur>=300) detected")

    print()

def test_dur_basic_stop():
    print("Testing dur basic _stop...")

    executed = []
    test_config = {
        "hiss": ("start", lambda: None),
        "hiss_stop:dur<300": ("brief", lambda: executed.append("brief")),
        "hiss_stop:dur>=300": ("sustained", lambda: executed.append("sustained")),
    }

    input_map = InputMap()
    input_map.setup(test_config)

    # Brief hiss
    input_map.execute("hiss")
    actions.sleep("50ms")
    input_map.execute("hiss_stop")
    assert executed == ["brief"], f"Failed: expected brief, got {executed}"
    print("  ✓ Brief hiss (dur<300) detected via _stop")

    # Sustained hiss
    executed.clear()
    input_map.execute("hiss")
    actions.sleep("350ms")
    input_map.execute("hiss_stop")
    assert executed == ["sustained"], f"Failed: expected sustained, got {executed}"
    print("  ✓ Sustained hiss (dur>=300) detected via _stop")

    print()

def test_dur_none_for_non_pair():
    print("Testing dur None for non-pair events...")

    executed = []
    test_config = {
        "left": ("press", lambda: None),
        "left_up:dur<300": ("tap", lambda: executed.append("tap")),
        "left_up:dur>=300": ("hold", lambda: executed.append("hold")),
        "pop": ("click", lambda: executed.append("click")),
    }

    input_map = InputMap()
    input_map.setup(test_config)

    # Pop has no start pair, so dur should be None and no dur condition should match
    input_map.execute("pop")
    assert executed == ["click"], f"Failed: got {executed}"
    print("  ✓ Non-pair event executes normally (dur=None, conditions don't match)")

    print()

def test_dur_context_param_injection():
    print("Testing dur context param injection...")

    executed = []
    test_config = {
        "left": ("press", lambda: None),
        "left_up:dur<300": ("tap", lambda dur: executed.append(f"tap_dur={dur is not None}")),
        "left_up:dur>=300": ("hold", lambda dur: executed.append(f"hold_dur={dur is not None}")),
    }

    input_map = InputMap()
    input_map.setup(test_config)

    input_map.execute("left")
    actions.sleep("50ms")
    input_map.execute("left_up")
    assert executed == ["tap_dur=True"], f"Failed: got {executed}"
    print("  ✓ dur received as lambda param via wrap_with_context")

    print()

def test_init_parse():
    print("Testing ':init' parsing...")

    assert parse_condition("init") == ("mode_age", "<", 300.0), parse_condition("init")
    assert parse_condition("init_150") == ("mode_age", "<", 150.0), parse_condition("init_150")
    assert parse_condition("initial") is None, "'initial' should not parse as init"
    assert parse_condition("init_") is None, "'init_' should not parse as init"
    print("  ✓ init / init_N desugar to mode_age")

    assert has_conditions("pop:init") is True
    assert has_conditions("pop:init_150") is True
    print("  ✓ init counts as a condition")

    cleaned, conditions = extract_conditions("pop:init:db_100")
    assert cleaned == "pop:db_100", f"Failed: got {cleaned}"
    assert conditions == [("mode_age", "<", 300.0)], f"Failed: got {conditions}"
    print("  ✓ init strips from the key and composes with debounce")

    print()

def test_init_basic():
    print("Testing ':init' window...")

    executed = []
    test_config = {
        "pop:init": ("gateway", lambda: executed.append("gateway")),
        "pop": ("normal", lambda: executed.append("normal")),
    }

    input_map = InputMap()
    input_map.setup(test_config)

    input_map.execute("pop")
    assert executed == ["gateway"], f"Failed: got {executed}"
    print("  ✓ Inside the window takes the init binding")

    executed.clear()
    actions.sleep("350ms")
    input_map.execute("pop")
    assert executed == ["normal"], f"Failed: got {executed}"
    print("  ✓ Past the window falls through to the plain key")

    print()

def test_init_explicit_window():
    print("Testing ':init_N' explicit window...")

    executed = []
    test_config = {
        "pop:init_150": ("gateway", lambda: executed.append("gateway")),
        "pop": ("normal", lambda: executed.append("normal")),
    }

    input_map = InputMap()
    input_map.setup(test_config)

    actions.sleep("50ms")
    input_map.execute("pop")
    assert executed == ["gateway"], f"Failed: got {executed}"

    executed.clear()
    actions.sleep("150ms")
    input_map.execute("pop")
    assert executed == ["normal"], f"Failed: got {executed}"
    print("  ✓ Per-key window is honored")

    print()

def test_init_no_binding_no_clock():
    print("Testing ':init' gating...")

    input_map = InputMap()
    input_map.setup({"pop": ("normal", lambda: None)})
    assert input_map.has_mode_age is False, "has_mode_age should be off without ':init'"

    input_map.setup({"pop:init": ("gateway", lambda: None), "pop": ("normal", lambda: None)})
    assert input_map.has_mode_age is True, "has_mode_age should be on with ':init'"
    print("  ✓ mode_age is only computed for maps that use it")

    print()

def test_init_restamps_on_mode_change():
    print("Testing ':init' restamps on mode change...")

    executed = []
    test_config = {
        "a": {
            "pop:init": ("a gateway", lambda: executed.append("a_gateway")),
            "pop": ("a normal", lambda: executed.append("a_normal")),
        },
        "b": {
            "pop": ("b normal", lambda: executed.append("b_normal")),
        },
    }

    input_map = InputMap()
    input_map.setup(test_config)

    input_map.execute("pop")
    assert executed == ["a_gateway"], f"Failed: got {executed}"

    executed.clear()
    actions.sleep("350ms")
    input_map.execute("pop")
    assert executed == ["a_normal"], f"Failed: got {executed}"
    print("  ✓ Window shuts while the mode stays put")

    # Re-entry serves mode 'a' from _mode_cache, where has_mode_age was missing.
    executed.clear()
    input_map.setup_mode("b")
    input_map.setup_mode("a")
    input_map.execute("pop")
    assert executed == ["a_gateway"], f"Failed: got {executed}"
    print("  ✓ Re-entering the mode reopens the window (cached path)")

    print()

def test_init_same_mode_does_not_restamp():
    print("Testing ':init' ignores a no-op mode set...")

    executed = []
    test_config = {
        "a": {
            "pop:init": ("gateway", lambda: executed.append("gateway")),
            "pop": ("normal", lambda: executed.append("normal")),
        },
        "b": {"pop": ("b", lambda: executed.append("b"))},
    }

    input_map = InputMap()
    input_map.setup(test_config)
    input_map.setup_mode("a")

    actions.sleep("350ms")
    input_map.setup_mode("a")
    input_map.execute("pop")
    assert executed == ["normal"], f"Failed: got {executed}"
    print("  ✓ Setting the mode it is already in does not reopen the window")

    print()

def test_init_rejects_else():
    print("Testing ':init' rejects an else branch...")

    executed = []
    test_config = {
        "pop:init": ("gateway", lambda: None),
        "pop:else": ("normal", lambda: None),
        "cluck": ("cluck", lambda: executed.append("cluck")),
    }

    input_map, printed = _load(test_config)
    _assert_bad(printed, "pop:else", "init")
    input_map.execute("cluck")
    assert executed == ["cluck"], f"Failed: rest of the map should work, got {executed}"
    print("  ✓ init with else prints an error, the rest loads")

    print()

def test_legend_hud_shapes():
    print("Testing legend rendering per modifier kind...")

    # (name, keys, expected display rows in order)
    cases = [
        ("lone base",
         ["pop"],
         ["pop"]),
        ("underscored base",
         ["left_up"],
         ["left up"]),
        ("throttle and debounce hidden",
         ["hiss:th_90", "hiss_stop:db_100"],
         ["hiss", "hiss stop"]),
        ("bare throttle hidden",
         ["hiss:th", "hiss_stop:db"],
         ["hiss", "hiss stop"]),
        ("dur pair drops the variable",
         ["left_up:dur<300", "left_up:dur>=300", "pop"],
         ["left up < 300", "left up >= 300", "pop"]),
        ("three dur branches",
         ["hiss_stop:dur<200", "hiss_stop:dur<600", "hiss_stop:dur>=600"],
         ["hiss stop < 200", "hiss stop < 600", "hiss stop >= 600"]),
        ("lone dur needs no modifier",
         ["left_up:dur<300", "pop"],
         ["left up", "pop"]),
        ("init",
         ["hiss:init", "hiss"],
         ["hiss init", "hiss"]),
        ("init keeps an explicit window",
         ["hiss:init_150", "hiss"],
         ["hiss init 150", "hiss"]),
        ("init composed with throttle",
         ["hiss:init:th_90", "hiss:th_90"],
         ["hiss init", "hiss"]),
        ("power branches drop the variable",
         ["pop:power>10", "pop:power<=10"],
         ["pop > 10", "pop <= 10"]),
        ("mixed variables keep both names",
         ["pop:power>10", "pop:f0<100"],
         ["pop power > 10", "pop f0 < 100"]),
        ("negative and fractional values",
         ["gaze:x<-0.5", "gaze:x>0.5", "gaze:else"],
         ["gaze < -0.5", "gaze > 0.5", "gaze else"]),
        ("now hidden, after shown",
         ["pop:now", "pop pop", "pop:after_100"],
         ["pop", "pop pop", "pop after 100"]),
        ("compose condition with throttle",
         ["pop:power>10:th_100", "pop"],
         ["pop > 10", "pop"]),
        ("combos are their own base",
         ["pop", "pop pop", "tut pop"],
         ["pop", "pop pop", "tut pop"]),
        ("cross-input modifier untouched",
         ["pedal + pop", "pop"],
         ["pedal + pop", "pop"]),
        ("variable pattern untouched",
         ["tut $noise", "pop"],
         ["tut $noise", "pop"]),
    ]

    for name, keys, expected in cases:
        commands = {key: (f"label {i}", lambda: None) for i, key in enumerate(keys)}
        legend = build_legend(commands)
        assert list(legend.keys()) == expected, f"Failed [{name}]: got {list(legend.keys())}"
        assert list(legend.values()) == [f"label {i}" for i in range(len(keys))], \
            f"Failed [{name}]: labels got reordered or dropped: {legend}"
        print(f"  ✓ {name}: {'  |  '.join(expected)}")

    print()

def test_legend_filters_empty_labels():
    print("Testing legend filters empty labels...")

    legend = build_legend({
        "pop": ("click", lambda: None),
        "cluck": ("", lambda: None),
        "sh_stop": ("", lambda: None),
        "hiss": "bare string label",
        "empty_tuple": (),
    })
    assert legend == {
        "pop": "click",
        "hiss": "bare string label",
    }, f"Failed: got {legend}"
    print("  ✓ Empty labels and empty tuples drop out; a bare string is a label")

    # An empty label still hides the row, but it must not make its sibling
    # look like a lone binding and lose the modifier that separates them.
    legend = build_legend({
        "left_up:dur<300": ("tap", lambda: None),
        "left_up:dur>=300": ("", lambda: None),
    })
    assert legend == {"left up": "tap"}, f"Failed: got {legend}"
    print("  ✓ A hidden sibling leaves the visible row bare")

    print()

def test_legend_real_world_map_unchanged():
    print("Testing legend on a real-world map...")

    # Shape taken from talon-game-celeste-parrot, the only consumer in the wild.
    # These rows must read the same as they did before the legend was unified.
    legend = build_legend({
        "sh:th_90":   ("jump 1", lambda: None),
        "sh_stop":    ("", lambda: None),
        "ss":         ("jump 2", lambda: None),
        "ss_stop":    ("", lambda: None),
        "ah":         ("left", lambda: None),
        "oh":         ("right", lambda: None),
        "pop":        ("dash f", lambda: None),
        "mm:th_90":   ("dash f down", lambda: None),
        "tut tut":    ("exit mode", lambda: None),
        "tut pop":    ("dash b", lambda: None),
        "cluck cluck": ("save", lambda: None),
    })
    assert legend == {
        "sh": "jump 1",
        "ss": "jump 2",
        "ah": "left",
        "oh": "right",
        "pop": "dash f",
        "mm": "dash f down",
        "tut tut": "exit mode",
        "tut pop": "dash b",
        "cluck cluck": "save",
    }, f"Failed: got {legend}"
    print("  ✓ No colons, no underscores, one row per sound")

    print()

def test_init_modifier_arms_clock():
    print("Testing modifier-side ':init' arms the clock...")

    input_map = InputMap()
    input_map.setup({
        "pedal_up": ("release", lambda: None),
        "pedal:init + pop": ("gated", lambda: None),
        "pop": ("plain", lambda: None),
    })
    assert input_map.has_mode_age is True, \
        "has_mode_age should be on for a modifier-side ':init'"
    print("  ✓ 'pedal:init + pop' is not a dead binding")

    print()

def test_init_modifier_edge_triggered_rejected():
    print("Testing modifier-side ':init' rejects an edge-triggered base...")

    executed = []
    input_map, printed = _load({
        "gaze:x<0.5": ("region", lambda: None),
        "gaze:else": ("off", lambda: None),
        "gaze:init + pop": ("gated", lambda: None),
        "pop": ("plain", lambda: executed.append("plain")),
    })
    _assert_bad(printed, "gaze:init + pop", "init")
    input_map.execute("pop")
    assert executed == ["plain"], f"Failed: rest of the map should work, got {executed}"
    print("  ✓ Region matching cannot hold mode_age, so it prints an error and the rest loads")

    print()

def test_parse_key():
    print("Testing parse_key...")

    got = parse_key("pop:power>10:th", init_window_ms=500)
    assert got["base"] == "pop" and got["inputs"] == ["pop"], got
    assert got["modifier"] is None and got["release_suffix"] == "", got
    assert got["segments"][0] == {"id": "condition", "text": "power>10",
                                  "value": ["power", ">", 10.0]}, got["segments"][0]
    assert got["segments"][1] == {"id": "th", "text": "th", "value": None, "ms": 100}, got["segments"][1]
    print("  ✓ condition and bare throttle")

    got = parse_key("left_up:dur<300")
    assert got["release_suffix"] == "_up" and got["release_of"] == "left", got
    assert got["segments"][0]["value"] == ["dur", "<", 300.0], got
    print("  ✓ _up is a release key, dur a condition")

    got = parse_key("pop:init", init_window_ms=500)
    assert got["segments"][0]["ms"] == 500, got
    got = parse_key("pop:init_150:after_200:now:else:huh")
    assert [s["id"] for s in got["segments"]] == ["init", "after", "now", "else", ""], got
    assert got["segments"][0]["ms"] == 150 and got["segments"][1]["ms"] == 200, got
    print("  ✓ init window, after, flags, unknown segment")

    got = parse_key("gaze:x<500 + pop pop:th_90")
    assert got["inputs"] == ["pop", "pop"] and got["segments"][0]["ms"] == 90, got
    assert got["modifier"]["base"] == "gaze", got
    assert got["modifier"]["segments"][0]["value"] == ["x", "<", 500.0], got
    print("  ✓ modifier side parsed on its own")

    got = parse_key("hiss_stop")
    assert got["release_suffix"] == "_stop" and got["release_of"] == "hiss", got
    assert parse_key("hiss_stop hiss")["release_suffix"] == "", "a combo is not a release key"
    print("  ✓ _stop, and not on a combo")

    print()

def test_types_match_parser():
    print("Testing input_map_types against the parser...")
    from .input_map_types import types
    got = types()
    ids = {name: [v["id"] for v in s["values"]] for name, s in got.items()}
    assert set(ids["condition_variable"]) == CONTEXT_KEYS, ids["condition_variable"]
    for seg in got["segment"]["values"]:
        assert seg["desc"] and seg["pattern"], seg
    for sample, seg_id in (("th_5", "th"), ("db", "db"), ("now", "now"),
                           ("init", "init"), ("f0>=2", "condition"), ("else", "else")):
        assert parse_segment(sample)["id"] == seg_id, (sample, parse_segment(sample))
    assert all(s["desc"] for s in got.values()), "every set is described"
    print("  ✓ sets come from the parser's tables")

    print()

def run_tests():
    print("="* 50)
    print("Running Input Map Tests")
    print("=" * 50)
    print()

    # Unit tests
    test_get_base_input()
    test_has_variables()
    test_extract_variables()
    test_pattern_to_regex()
    test_match_variable_pattern()
    test_validate_variable_action()

    # Integration tests
    test_input_map_single_command()
    test_input_map_combo()
    test_input_map_immediate_combo()
    test_input_map_variable_pattern()
    test_input_map_modes()
    test_input_map_now_modifier()
    test_input_map_continuous_pairs()
    test_input_map_throttle()
    test_input_map_debounce()

    # Conditional tests (unit)
    test_parse_condition()
    test_extract_conditions()
    test_evaluate_conditions()

    # Conditional tests (integration)
    test_input_map_conditional_basic()
    test_input_map_conditional_no_match()
    test_input_map_conditional_with_fallback()
    test_input_map_conditional_missing_context()
    test_input_map_conditional_multi_condition()

    # Context params tests
    test_input_map_context_params_basic()
    test_input_map_context_params_multi()
    test_input_map_context_params_zero_arg()
    test_input_map_context_params_variable_excluded()
    test_input_map_context_params_conditional()
    test_input_map_context_params_throttle()

    # Edge-triggered tests (unit)
    test_has_conditions_else()
    test_extract_conditions_else()

    # Edge-triggered tests (integration)
    test_input_map_edge_triggered_basic()
    test_input_map_edge_triggered_else_fires()
    test_input_map_edge_triggered_with_context_params()
    test_input_map_edge_triggered_mode_reset()
    test_input_map_no_else_unchanged()
    test_input_map_edge_triggered_negative_threshold()

    # Spread override tests
    test_input_map_spread_override_same_modifier()
    test_input_map_spread_override_different_modifier()
    test_input_map_spread_override_modes()

    # Channel tests
    test_channel_register_unregister()
    test_channel_re_registration()
    test_channel_get()
    test_channel_handle()
    test_channel_modes()
    test_channel_get_legend()
    test_channel_events()

    # Single tests
    test_normalize_single_map_simple()
    test_normalize_single_map_tuple()
    test_normalize_single_map_expanded()
    test_single_handle_basic()
    test_single_handle_tuple()
    test_single_handle_expanded()
    test_single_mode_switching()
    test_single_mode_cycle()
    test_single_mode_get()
    test_single_first_mode_is_default()
    test_single_get_legend()
    test_single_independent_state()
    test_single_auto_reregister()
    test_single_mode_revert()

    # Mode revert tests
    test_mode_revert()
    test_channel_mode_revert()

    # Bool handler tests
    test_handle_bool_basic()
    test_handle_bool_channel()
    test_handle_bool_single()

    # Cross-input modifier tests (unit)
    test_has_modifier()
    test_extract_modifier()
    test_validate_modifier()

    # Cross-input modifier tests (integration)
    test_modifier_held_basic()
    test_modifier_edge_triggered()
    test_modifier_release_resets_held()
    test_modifier_with_combo_activator()
    test_modifier_mode_switch_resets()
    test_modifier_has_modifiers_false()
    test_modifier_fallthrough()
    test_modifier_conditional()

    # Edge debounce tests
    test_edge_debounce_delays_transition()
    test_edge_debounce_flicker_settles()
    test_edge_debounce_active_region_stable()
    test_edge_debounce_zero_unchanged()
    test_edge_debounce_mode_switch_cancels()

    # Duration (dur) tests
    test_legend_multiple_cases()
    test_dur_up_creates_base_pairs()
    test_dur_basic_up()
    test_dur_basic_stop()
    test_dur_none_for_non_pair()
    test_dur_context_param_injection()

    # Legend tests
    test_legend_hud_shapes()
    test_legend_filters_empty_labels()
    test_legend_real_world_map_unchanged()

    # Mode init window (':init') tests
    test_init_parse()
    test_init_basic()
    test_init_explicit_window()
    test_init_no_binding_no_clock()
    test_init_restamps_on_mode_change()
    test_init_same_mode_does_not_restamp()
    test_init_modifier_arms_clock()

    # Key parsing and types
    test_parse_key()
    test_types_match_parser()

    failed = run_key_behavior_tests()
    bench()

    print()
    print("=" * 50)
    print(f"{len(failed)} key behavior tests failing" if failed else "All tests passed!")
    print("=" * 50)

# Key behavior (1.3.0)
#
# One test per decision in the workspace note input-map-key-behavior.md.
# Written before the fix, so some fail until it lands. run_key_behavior_tests()
# reports every test instead of stopping at the first failure.

# Ground rules

def test_key_bad_key_skips_only_itself():
    print("Testing a bad key skips only itself...")

    executed = []
    input_map, printed = _load({
        "pop": ("click", lambda: executed.append("pop")),
        "cluck:foo": ("bad", lambda: executed.append("cluck")),
    })
    _assert_bad(printed, "cluck:foo", "foo", "now")
    print("  ✓ Error names the key, the unknown segment, and the valid ones")

    input_map.execute("pop")
    input_map.execute("cluck")
    assert executed == ["pop"], f"Failed: got {executed}"
    print("  ✓ The good key fires, the bad key doesn't")

    print()

def test_key_segment_order():
    print("Testing segment order doesn't matter...")

    for key in ("pop:th_200:power>10", "pop:power>10:th_200"):
        executed = []
        input_map, printed = _load({key: ("loud", lambda: executed.append("loud"))})
        _assert_clean(printed)
        input_map.execute("pop", power=20.0)
        input_map.execute("pop", power=20.0)
        assert executed == ["loud"], f"Failed: {key} got {executed}"
    print("  ✓ Both orders throttle the condition the same way")

    a = parse_key("pop:th_200:power>10")
    b = parse_key("pop:power>10:th_200")
    assert sorted(s["text"] for s in a["segments"]) == sorted(s["text"] for s in b["segments"]), (a, b)
    print("  ✓ key_parse reads the same segments")

    print()

def test_key_repeated_segment():
    print("Testing the same segment twice is a bad key...")

    _, printed = _load({"pop:th:th_90": ("x", lambda: None)})
    _assert_bad(printed, "pop:th:th_90")
    _, printed = _load({
        "hiss": ("start", lambda: None),
        "hiss_stop:db_50:db_100": ("x", lambda: None),
    })
    _assert_bad(printed, "hiss_stop:db_50:db_100")
    print("  ✓ Repeated th and db print errors")

    print()

def test_key_condition_range():
    print("Testing two conditions on one variable form a range...")

    executed = []
    input_map, printed = _load({"pop:power>10:power<50": ("mid", lambda: executed.append("mid"))})
    _assert_clean(printed)
    for power in (30.0, 5.0, 60.0):
        input_map.execute("pop", power=power)
    assert executed == ["mid"], f"Failed: got {executed}"
    print("  ✓ Fires at 30, not at 5 or 60")

    _, printed = _load({"pop:power>50:power<10": ("never", lambda: None)})
    _assert_bad(printed, "pop:power>50:power<10")
    print("  ✓ A range that can never match is a bad key")

    print()

def test_key_release_suffixes_reserved():
    print("Testing _up and _stop always mean a release...")

    executed = []
    input_map, printed = _load({
        "left": ("press", lambda: executed.append("press")),
        "left_up:dur<300": ("tap", lambda: executed.append("tap")),
        "left_up:dur>=300": ("hold", lambda: executed.append("hold")),
    })
    _assert_clean(printed)
    input_map.execute("left")
    actions.sleep("50ms")
    input_map.execute("left_up")
    assert executed == ["press", "tap"], f"Failed: got {executed}"
    print("  ✓ Press, then exactly one release")

    assert parse_key("dpad_up")["release_of"] == "dpad", parse_key("dpad_up")
    print("  ✓ dpad_up reads as the release of dpad (known limitation)")

    print()

# Releases

def test_key_release_only_mapped():
    print("Testing a release fires when only the release is mapped...")

    executed = []
    input_map, printed = _load({"left_stop": ("release", lambda: executed.append("release"))})
    _assert_clean(printed)
    input_map.execute("left")
    input_map.execute("left_stop")
    assert executed == ["release"], f"Failed: got {executed}"
    print("  ✓ left_stop fires")

    for suffix in ("_stop", "_up"):
        executed = []
        input_map, printed = _load({
            f"left{suffix}:dur<300": ("tap", lambda: executed.append("tap")),
            f"left{suffix}:dur>=300": ("hold", lambda: executed.append("hold")),
        })
        _assert_clean(printed)
        input_map.execute("left")
        actions.sleep("100ms")
        input_map.execute(f"left{suffix}")
        assert executed == ["tap"], f"Failed: {suffix} got {executed}"
    print("  ✓ Picks tap vs hold by hold time, with _stop and _up")

    print()

def test_key_combo_hold_back():
    print("Testing the 90ms hold-back after a combo ending in a continuous noise...")

    executed = []
    input_map, printed = _load({
        "pop hiss": ("combo", lambda: executed.append("combo")),
        "hiss:th_90": ("scroll", lambda: executed.append("scroll")),
        "hiss_stop": ("stop", lambda: None),
    })
    _assert_clean(printed)
    input_map.execute("pop")
    input_map.execute("hiss")
    assert executed == ["combo"], f"Failed: got {executed}"
    input_map.execute("hiss")
    assert executed == ["combo"], f"Failed: hiss inside 90ms should be held back, got {executed}"
    print("  ✓ hiss right after the combo doesn't fire")

    actions.sleep("120ms")
    input_map.execute("hiss")
    assert executed == ["combo", "scroll"], f"Failed: got {executed}"
    print("  ✓ hiss after 90ms fires")

    print()

def test_key_throttle_on_release():
    print("Testing th on a release is a bad key...")

    _, printed = _load({"hiss": ("start", lambda: None), "hiss_stop:th_200": ("x", lambda: None)})
    _assert_bad(printed, "hiss_stop:th_200", "hiss_stop:db_200")
    _, printed = _load({"left": ("press", lambda: None), "left_up:th": ("x", lambda: None)})
    _assert_bad(printed, "left_up:th", "left_up:db")
    print("  ✓ Error points to db on the release")

    print()

def test_key_debounce_release_bridges_gaps():
    print("Testing db on a release bridges gaps...")

    executed = []
    input_map, printed = _load({
        "hiss": ("start", lambda: executed.append("start")),
        "hiss_stop:db_100": ("stop", lambda: executed.append("stop")),
    })
    _assert_clean(printed)
    input_map.execute("hiss")
    input_map.execute("hiss_stop")
    actions.sleep("50ms")
    input_map.execute("hiss")
    actions.sleep("200ms")
    assert executed == ["start"], f"Failed: got {executed}"
    print("  ✓ hiss inside the wait neither stops nor fires again")

    print()

def test_key_debounce_misuse():
    print("Testing db where it can't work points to what does...")

    _, printed = _load({"hiss:db_100": ("x", lambda: None)})
    _assert_bad(printed, "hiss:db_100", "stop", "hiss:dur>=100", "hiss_stop:db_100")
    print("  ✓ db on a start points to dur>=N and to db on the stop")

    _, printed = _load({"pop:db_100": ("x", lambda: None)})
    _assert_bad(printed, "pop:db_100", "stop", "pop:th_100")
    print("  ✓ db on a key with no stop points to th")

    print()

def test_key_after_removed():
    print("Testing after is removed, with a pointer to what replaces it...")

    executed = []
    input_map, printed = _load({
        "pop": ("click", lambda: executed.append("pop")),
        "pop:after_200": ("hop", lambda: executed.append("after")),
    })
    _assert_bad(printed, "pop:after_200", "removed", "combo", "pop:now")
    input_map.execute("pop")
    actions.sleep("300ms")
    assert executed == ["pop"], f"Failed: got {executed}"
    print("  ✓ Error says removed, explains the combo wait and now; pop still works")

    print()

def test_key_dur_start():
    print("Testing dur>=N on a start fires once held that long...")

    executed = []
    input_map, printed = _load({"hiss:dur>=100": ("held", lambda: executed.append("held"))})
    _assert_clean(printed)
    input_map.execute("hiss")
    actions.sleep("50ms")
    input_map.execute("hiss_stop")
    actions.sleep("100ms")
    assert executed == [], f"Failed: 50ms hiss should fire nothing, got {executed}"
    print("  ✓ A 50ms hiss fires nothing")

    input_map.execute("hiss")
    actions.sleep("150ms")
    assert executed == ["held"], f"Failed: got {executed}"
    input_map.execute("hiss_stop")
    print("  ✓ Fires at 100ms, before the release")

    print()

def test_key_dur_start_stages():
    print("Testing dur>=N stages fire in one hold...")

    executed = []
    input_map, printed = _load({
        "hiss:dur>=100": ("short", lambda: executed.append("100")),
        "hiss:dur>=600": ("long", lambda: executed.append("600")),
    })
    _assert_clean(printed)
    input_map.execute("hiss")
    actions.sleep("300ms")
    assert executed == ["100"], f"Failed: got {executed}"
    actions.sleep("400ms")
    assert executed == ["100", "600"], f"Failed: got {executed}"
    input_map.execute("hiss_stop")
    print("  ✓ Both fire, in order")

    print()

def test_key_dur_start_upper_bound():
    print("Testing dur<N on a start is a bad key...")

    _, printed = _load({"hiss:dur<100": ("x", lambda: None)})
    _assert_bad(printed, "hiss:dur<100", "hiss_stop:dur<100")
    print("  ✓ Error points to the stop")

    print()

def test_key_dur_start_with_stop():
    print("Testing a dur start with its stop...")

    executed = []
    input_map, printed = _load({
        "hiss:dur>=100": ("start", lambda: executed.append("start")),
        "hiss_stop:db_100": ("stop", lambda: executed.append("stop")),
    })
    _assert_clean(printed)
    input_map.execute("hiss")
    actions.sleep("200ms")
    assert executed == ["start"], f"Failed: got {executed}"
    input_map.execute("hiss_stop")
    actions.sleep("200ms")
    assert executed == ["start", "stop"], f"Failed: got {executed}"
    print("  ✓ Normal cycle: start then stop")

    executed.clear()
    input_map, printed = _load({
        "hiss:dur>=100": ("start", lambda: executed.append("start")),
        "hiss_stop": ("stop", lambda: executed.append("stop")),
    })
    input_map.execute("hiss")
    actions.sleep("50ms")
    input_map.execute("hiss_stop")
    actions.sleep("150ms")
    assert executed == [], f"Failed: got {executed}"
    print("  ✓ Early release: the start never fired, so the stop doesn't either")

    print()

def test_key_dur_start_impossible_stop():
    print("Testing a dur stop that a dur start rules out...")

    _, printed = _load({
        "hiss:dur>=100": ("start", lambda: None),
        "hiss_stop:dur<100": ("stop", lambda: None),
    })
    _assert_bad(printed, "hiss_stop:dur<100")
    print("  ✓ Load error on the stop")

    print()

def test_key_dur_start_repeated_starts():
    print("Testing repeated starts during one hold...")

    executed = []
    input_map, printed = _load({
        "hiss:dur>=100": ("start", lambda: executed.append("start")),
        "hiss_stop:db_170": ("stop", lambda: executed.append("stop")),
    })
    _assert_clean(printed)
    input_map.execute("hiss")         # t=0
    actions.sleep("30ms")
    input_map.execute("hiss")         # t=30, same hold
    actions.sleep("30ms")
    input_map.execute("hiss_stop")    # t=60, stop waits 170ms
    actions.sleep("50ms")
    input_map.execute("hiss")         # t=110, inside the wait: same hold
    actions.sleep("90ms")
    assert executed == ["start"], f"Failed: got {executed}"
    print("  ✓ The start fires once, timed from the first hiss")

    input_map.execute("hiss_stop")
    actions.sleep("250ms")
    assert executed == ["start", "stop"], f"Failed: got {executed}"
    print("  ✓ The real stop fires")

    print()

def test_key_now_on_release():
    print("Testing now on a release is a bad key...")

    _, printed = _load({"hiss": ("start", lambda: None), "hiss_stop:now": ("x", lambda: None)})
    _assert_bad(printed, "hiss_stop:now")
    print("  ✓ Load error")

    print()

def test_key_init_on_release():
    print("Testing init on a release follows the start that fired...")

    executed = []
    input_map, printed = _load({
        "hiss": ("start", lambda: executed.append("start")),
        "hiss_stop": ("stop", lambda: executed.append("stop")),
        "hiss:init_150": ("init", lambda: executed.append("init")),
        "hiss_stop:init_150": ("init stop", lambda: executed.append("init_stop")),
    })
    _assert_clean(printed)
    actions.sleep("50ms")
    input_map.execute("hiss")
    actions.sleep("300ms")
    input_map.execute("hiss_stop")
    assert executed == ["init", "init_stop"], f"Failed: got {executed}"
    print("  ✓ The init stop fires after the window closed")

    executed.clear()
    input_map, printed = _load({
        "hiss": ("start", lambda: executed.append("start")),
        "hiss_stop": ("stop", lambda: executed.append("stop")),
        "hiss:init_150": ("init", lambda: executed.append("init")),
    })
    _assert_clean(printed)
    input_map.execute("hiss")
    actions.sleep("300ms")
    input_map.execute("hiss_stop")
    assert executed == ["init"], f"Failed: got {executed}"
    print("  ✓ With no init stop, the release fires nothing")

    print()

def test_key_parrot_condition_on_release():
    print("Testing power on a release is a bad key...")

    _, printed = _load({"hiss": ("start", lambda: None), "hiss_stop:power>10": ("x", lambda: None)})
    _assert_bad(printed, "hiss_stop:power>10")
    print("  ✓ Load error")

    print()

# Each segment alone

def test_key_throttle_zero():
    print("Testing th_0 is a bad key...")

    _, printed = _load({"pop:th_0": ("x", lambda: None)})
    _assert_bad(printed, "pop:th_0")
    print("  ✓ Load error")

    print()

def test_key_throttle_per_sound():
    print("Testing one throttle per sound...")

    _, printed = _load({
        "pop:th_50": ("normal", lambda: None),
        "pop:init:th_50": ("init", lambda: None),
    })
    _assert_clean(printed)
    print("  ✓ The same value on two keys loads")

    _, printed = _load({
        "pop:th_50": ("normal", lambda: None),
        "pop:init:th_200": ("init", lambda: None),
    })
    assert "pop:th_50" in printed or "pop:init:th_200" in printed, f"Failed: got:\n{printed}"
    print("  ✓ Two values is a bad key")

    executed = []
    input_map, printed = _load({
        "pop:power>10:th_200": ("loud", lambda: executed.append("loud")),
        "pop:else": ("soft", lambda: executed.append("soft")),
    })
    _assert_clean(printed)
    input_map.execute("pop", power=5.0)
    input_map.execute("pop", power=5.0)
    input_map.execute("pop", power=20.0)
    actions.sleep("250ms")
    input_map.execute("pop", power=5.0)
    assert executed == ["soft", "soft"], f"Failed: got {executed}"
    print("  ✓ The throttle covers every key of the sound, else included")

    print()

def test_key_now_alone():
    print("Testing now with no combo to wait for...")

    executed = []
    input_map, printed = _load({"pop:now": ("click", lambda: executed.append("pop"))})
    _assert_clean(printed)
    input_map.execute("pop")
    assert executed == ["pop"], f"Failed: got {executed}"
    print("  ✓ Fires immediately")

    print()

def test_key_plain_with_conditions():
    print("Testing a plain key next to conditioned keys is a bad key...")

    executed = []
    input_map, printed = _load({
        "pop": ("plain", lambda: executed.append("plain")),
        "pop:power>10": ("loud", lambda: executed.append("loud")),
    })
    _assert_bad(printed, "pop", "pop:else")
    input_map.execute("pop", power=20.0)
    input_map.execute("pop", power=5.0)
    assert executed == ["loud"], f"Failed: got {executed}"
    print("  ✓ Error points to else; the plain key is skipped")

    _, printed = _load({
        "hiss": ("plain", lambda: None),
        "hiss:init": ("init", lambda: None),
    })
    _assert_clean(printed)
    print("  ✓ init is exempt")

    print()

def test_key_else_per_event_for_parrot():
    print("Testing else on parrot conditions fires every event...")

    executed = []
    input_map, printed = _load({
        "pop:power>10": ("loud", lambda: executed.append("loud")),
        "pop:else": ("soft", lambda: executed.append("soft")),
    })
    _assert_clean(printed)
    for power in (20.0, 20.0, 5.0, 5.0):
        input_map.execute("pop", power=power)
    assert executed == ["loud", "loud", "soft", "soft"], f"Failed: got {executed}"
    print("  ✓ Two loud pops fire twice, two soft pops fire else twice")

    print()

def test_key_else_edge_for_streams():
    print("Testing else on x/y/value conditions fires once per change...")

    executed = []
    input_map, printed = _load({
        "gaze:x<-0.5": ("left", lambda: executed.append("left")),
        "gaze:else": ("neutral", lambda: executed.append("neutral")),
    })
    _assert_clean(printed)
    for x in (0.0, 0.0, -1.0, -1.0, 0.0):
        input_map.execute("gaze", x=x, y=0.0)
    assert executed == ["neutral", "left", "neutral"], f"Failed: got {executed}"
    print("  ✓ Repeated values in one region fire once")

    print()

def test_key_condition_kinds_mixed():
    print("Testing parrot and stream conditions on one input is a bad key...")

    _, printed = _load({
        "pop:power>10": ("loud", lambda: None),
        "pop:x<0": ("left", lambda: None),
        "pop:else": ("other", lambda: None),
    })
    assert "pop:power>10" in printed or "pop:x<0" in printed, f"Failed: got:\n{printed}"
    print("  ✓ Load error")

    print()

def test_key_condition_numbers():
    print("Testing which numbers each condition variable takes...")

    for config in (
        {"gaze:x<-0.5": ("left", lambda: None), "gaze:else": ("off", lambda: None)},
        {"dimple_left:value>0.5": ("on", lambda: None), "dimple_left:value<-0.1": ("neg", lambda: None)},
    ):
        _, printed = _load(config)
        _assert_clean(printed)
    print("  ✓ x, y, value take negative decimals")

    for key in ("pop:power>-5", "pop:power>10.5"):
        _, printed = _load({key: ("x", lambda: None)})
        _assert_bad(printed, key)
    print("  ✓ power takes whole numbers, not negative")

    print()

def test_key_else_needs_condition():
    print("Testing else needs a condition on the same input...")

    _, printed = _load({"pop:else": ("x", lambda: None)})
    _assert_bad(printed, "pop:else", "condition")
    _, printed = _load({"pop:power>10": ("loud", lambda: None), "pop:else": ("soft", lambda: None)})
    _assert_clean(printed)
    print("  ✓ Alone it's a bad key; with a condition it loads")

    print()

def test_key_init_with_condition():
    print("Testing init and a condition on one key...")

    executed = []
    input_map, printed = _load({"pop:init_150:power>10": ("loud start", lambda: executed.append("hit"))})
    _assert_clean(printed)
    input_map.execute("pop", power=5.0)
    input_map.execute("pop", power=20.0)
    actions.sleep("200ms")
    input_map.execute("pop", power=20.0)
    assert executed == ["hit"], f"Failed: got {executed}"
    print("  ✓ Only a loud pop inside the window fires")

    print()

def test_key_else_with_throttle():
    print("Testing th on an else key is a bad key...")

    _, printed = _load({
        "pop:power>10": ("loud", lambda: None),
        "pop:else:th_50": ("soft", lambda: None),
    })
    _assert_bad(printed, "pop:else:th_50", "pop:power>10:th_50")
    print("  ✓ Error points to the conditioned key")

    print()

def test_key_experimental_flags():
    print("Testing experimental segments are flagged in input_map_types...")
    from .input_map_types import types

    variables = {v["id"]: v for v in types()["condition_variable"]["values"]}
    for var in ("f0", "f1", "f2"):
        assert variables[var].get("experimental"), variables[var]
    assert not variables["power"].get("experimental"), variables["power"]
    print("  ✓ Pitch conditions are experimental, power isn't")

    print()

def test_key_later_key_replaces():
    print("Testing a later key replaces one for the same input and conditions...")

    executed = []
    default_config = {
        "mm:th_300": ("f-down", lambda: executed.append("mm default")),
        "sh:th_90": ("jump", lambda: executed.append("sh default")),
        "ss": ("jump 2", lambda: executed.append("ss default")),
    }
    move_config = {
        **default_config,
        "mm": ("f-down", lambda: executed.append("mm")),
        "sh:th_300": ("jump", lambda: executed.append("sh")),
        "ss:th_300": ("dash", lambda: executed.append("ss")),
    }
    input_map, printed = _load(move_config)
    _assert_clean(printed)
    input_map.execute("mm")
    input_map.execute("mm")
    input_map.execute("sh")
    actions.sleep("150ms")
    input_map.execute("sh")
    input_map.execute("ss")
    assert executed == ["mm", "mm", "sh", "ss"], f"Failed: got {executed}"
    print("  ✓ Celeste-style spread: overrides load and win, with their own throttles")

    executed = []
    input_map, printed = _load({
        "pop:power>10": ("first", lambda: executed.append("first")),
        "pop:power>10:th_200": ("second", lambda: executed.append("second")),
    })
    _assert_clean(printed)
    input_map.execute("pop", power=20.0)
    input_map.execute("pop", power=20.0)
    assert executed == ["second"], f"Failed: got {executed}"
    print("  ✓ Same conditions: the later key replaces the earlier")

    print()

# Combos

def test_key_segments_on_combos():
    print("Testing segments on combos and variable keys are bad keys...")

    _, printed = _load({"pop cluck:th": ("x", lambda: None)})
    _assert_bad(printed, "pop cluck:th")
    _, printed = _load({"tut $noise:th": ("x", lambda noise: None)})
    _assert_bad(printed, "tut $noise:th")
    print("  ✓ Load errors")

    print()

def test_key_conditioned_combo_prefix():
    print("Testing a conditioned pop as a combo prefix...")

    executed = []
    input_map, printed = _load({
        "pop:power>10": ("loud", lambda: executed.append("loud")),
        "pop:else": ("soft", lambda: executed.append("soft")),
        "pop cluck": ("combo", lambda: executed.append("combo")),
    })
    _assert_clean(printed)
    input_map.execute("pop", power=5.0)
    input_map.execute("cluck")
    assert executed == ["combo"], f"Failed: got {executed}"
    print("  ✓ Soft pop then cluck fires the combo")

    input_map.execute("pop", power=20.0)
    actions.sleep("350ms")
    assert executed == ["combo", "loud"], f"Failed: got {executed}"
    print("  ✓ Loud pop alone fires its condition after the combo window")

    print()

# Modes and channels: today's behavior, pinned

def test_key_mode_switch_timers():
    print("Testing timers across a mode switch...")

    executed = []
    input_map, printed = _load({
        "default": {"pop:th_300": ("a", lambda: executed.append("a"))},
        "b": {"pop:th_300": ("b", lambda: executed.append("b"))},
    })
    input_map.execute("pop")
    input_map.setup_mode("b")
    input_map.execute("pop")
    assert executed == ["a"], f"Failed: got {executed}"
    print("  ✓ A throttle survives the switch")

    executed = []
    input_map, printed = _load({
        "default": {
            "pop": ("a", lambda: executed.append("a")),
            "pop pop": ("aa", lambda: executed.append("aa")),
        },
        "b": {"pop": ("b", lambda: executed.append("b"))},
    })
    input_map.execute("pop")
    input_map.setup_mode("b")
    actions.sleep("350ms")
    assert executed == [], f"Failed: got {executed}"
    print("  ✓ A pending combo is dropped")

    executed = []
    input_map, printed = _load({
        "default": {
            "hiss": ("start", lambda: executed.append("start")),
            "hiss_stop:db_100": ("stop a", lambda: executed.append("stop_a")),
        },
        "b": {
            "hiss": ("start b", lambda: executed.append("start_b")),
            "hiss_stop": ("stop b", lambda: executed.append("stop_b")),
        },
    })
    input_map.execute("hiss")
    input_map.execute("hiss_stop")
    input_map.setup_mode("b")
    actions.sleep("200ms")
    assert executed == ["start", "stop_a"], f"Failed: got {executed}"
    print("  ✓ A pending debounced stop still fires the old mode's action")

    print()

def test_key_channel_timers():
    print("Testing timers are per channel...")

    executed = []
    for name in ("test_key_a", "test_key_b"):
        if name in _channels:
            channel_unregister(name)
        channel_register(name, {"pop:th_300": (name, lambda name=name: executed.append(name))})
    channel_handle("test_key_a", "pop")
    channel_handle("test_key_b", "pop")
    assert executed == ["test_key_a", "test_key_b"], f"Failed: got {executed}"
    print("  ✓ A throttle in one channel doesn't hold the other")
    channel_unregister("test_key_a")
    channel_unregister("test_key_b")

    print()

def run_key_behavior_tests():
    """Run every key behavior test, reporting each failure without stopping. Returns the failures."""
    print("=" * 50)
    print("Key behavior (1.3.0)")
    print("=" * 50)
    print()

    tests = [
        test_key_bad_key_skips_only_itself,
        test_modifier_parse_validation_error,
        test_init_rejects_else,
        test_init_modifier_edge_triggered_rejected,
        test_key_segment_order,
        test_key_repeated_segment,
        test_key_condition_range,
        test_key_release_suffixes_reserved,
        test_key_release_only_mapped,
        test_key_combo_hold_back,
        test_key_throttle_on_release,
        test_key_debounce_release_bridges_gaps,
        test_key_debounce_misuse,
        test_key_after_removed,
        test_key_dur_start,
        test_key_dur_start_stages,
        test_key_dur_start_upper_bound,
        test_key_dur_start_with_stop,
        test_key_dur_start_impossible_stop,
        test_key_dur_start_repeated_starts,
        test_key_now_on_release,
        test_key_init_on_release,
        test_key_parrot_condition_on_release,
        test_key_throttle_zero,
        test_key_throttle_per_sound,
        test_key_now_alone,
        test_key_plain_with_conditions,
        test_key_else_per_event_for_parrot,
        test_key_else_edge_for_streams,
        test_key_condition_kinds_mixed,
        test_key_condition_numbers,
        test_key_else_needs_condition,
        test_key_init_with_condition,
        test_key_else_with_throttle,
        test_key_experimental_flags,
        test_key_later_key_replaces,
        test_key_segments_on_combos,
        test_key_conditioned_combo_prefix,
        test_key_mode_switch_timers,
        test_key_channel_timers,
    ]
    failed = []
    for test in tests:
        try:
            test()
        except Exception as e:
            failed.append(test.__name__)
            print(f"  ✗ {test.__name__}: {type(e).__name__}: {e}")
            print()
    print(f"Key behavior: {len(tests) - len(failed)} of {len(tests)} pass")
    if failed:
        print("Failing: " + ", ".join(failed))
    return failed

def bench(rounds: int = 2000):
    """Microseconds per input through a Celeste-like map: conditions, a release
    pair, a throttle, a combo and plain keys. For comparing before and after a change."""
    import time

    noop = lambda: None
    input_map = InputMap(event_trigger=lambda event: None)
    input_map.setup({
        "pop:power>10": ("loud", noop),
        "pop:else": ("soft", noop),
        "ss": ("hold", noop),
        "ss_stop": ("release", noop),
        "sh:th_90": ("jump", noop),
        "sh_stop": ("", noop),
        "tut ee": ("combo", noop),
        "cluck": ("plain", noop),
    })
    sequence = (
        ("pop", 20.0), ("pop", 5.0), ("ss", None), ("ss_stop", None),
        ("sh", None), ("sh", None), ("tut", None), ("ee", None), ("cluck", None),
    )
    start = time.perf_counter()
    for _ in range(rounds):
        for name, power in sequence:
            input_map.execute(name, power=power)
    elapsed = time.perf_counter() - start
    per_input = elapsed / (rounds * len(sequence)) * 1e6
    print(f"bench: {per_input:.1f} us per input ({rounds * len(sequence)} inputs)")
