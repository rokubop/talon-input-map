from talon import actions
from .input_map import InputMap, input_map_saved, input_map_mode_revert
from .input_map_parse import (
    get_base_input,
    extract_variables,
    pattern_to_regex,
    match_variable_pattern,
    has_variables,
    has_conditions,
    validate_variable_action,
    parse_condition,
    extract_conditions,
    evaluate_conditions,
)
from .input_map_profile import (
    profile_register,
    profile_unregister,
    profile_list,
    profile_get,
    profile_handle,
    profile_mode_set,
    profile_mode_get,
    profile_mode_cycle,
    profile_mode_revert,
    profile_get_legend,
    profile_event_register,
    profile_event_unregister,
    _profiles,
    _profile_callbacks,
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
        "pop:db_100": ("debounced action", lambda: executed.append("debounced")),
    }

    input_map = InputMap()
    input_map.setup(test_config)

    # First execution should schedule but not execute immediately
    input_map.execute("pop")
    assert executed == [], f"Failed: debounced command executed immediately, got {executed}"
    print("  ✓ Debounced command doesn't execute immediately")

    # Second execution should cancel first and reschedule
    input_map.execute("pop")
    assert executed == [], f"Failed: debounced command executed too early, got {executed}"
    print("  ✓ Rapid debounced calls don't execute early")

    # After debounce period, should execute
    actions.sleep("110ms")
    assert executed == ["debounced"], f"Failed: didn't execute after debounce period, got {executed}"
    print("  ✓ Executes after debounce period")

    print()

def test_profile_register_unregister():
    print("Testing profile register/unregister...")

    # Clean up any existing test profile
    if "test_profile" in _profiles:
        profile_unregister("test_profile")

    test_config = {
        "pop": ("action A", lambda: None),
    }

    # Register
    profile_register("test_profile", test_config)
    assert "test_profile" in profile_list(), f"Failed: profile not in list"
    print("  ✓ Profile registered and appears in list")

    # Unregister
    profile_unregister("test_profile")
    assert "test_profile" not in profile_list(), f"Failed: profile still in list"
    print("  ✓ Profile unregistered")

    print()

def test_profile_re_registration():
    print("Testing profile re-registration warning...")

    # Clean up
    if "test_reregister" in _profiles:
        profile_unregister("test_reregister")

    executed = []
    config1 = {"pop": ("first", lambda: executed.append("first"))}
    config2 = {"pop": ("second", lambda: executed.append("second"))}

    profile_register("test_reregister", config1)
    profile_register("test_reregister", config2)  # Should warn and keep first

    # Execute and verify first config is kept
    profile_handle("test_reregister", "pop")
    assert executed == ["first"], f"Failed: got {executed}"
    print("  ✓ Re-registration keeps original profile")

    profile_unregister("test_reregister")
    print()

def test_profile_get():
    print("Testing profile_get...")

    if "test_get" in _profiles:
        profile_unregister("test_get")

    test_config = {
        "default": {"pop": ("default action", lambda: None)},
        "combat": {"pop": ("combat action", lambda: None)},
    }

    profile_register("test_get", test_config)

    # Get full config
    full = profile_get("test_get")
    assert "default" in full and "combat" in full, f"Failed: got {full}"
    print("  ✓ Get full config")

    # Get specific mode
    combat = profile_get("test_get", "combat")
    assert "pop" in combat, f"Failed: got {combat}"
    print("  ✓ Get specific mode")

    profile_unregister("test_get")
    print()

def test_profile_handle():
    print("Testing profile_handle...")

    if "test_handle" in _profiles:
        profile_unregister("test_handle")

    executed = []
    test_config = {
        "pop": ("action A", lambda: executed.append("A")),
        "cluck": ("action B", lambda: executed.append("B")),
    }

    profile_register("test_handle", test_config)

    profile_handle("test_handle", "pop")
    assert executed == ["A"], f"Failed: got {executed}"
    print("  ✓ Profile handle executes action")

    profile_handle("test_handle", "cluck")
    assert executed == ["A", "B"], f"Failed: got {executed}"
    print("  ✓ Profile handle executes multiple actions")

    profile_unregister("test_handle")
    print()

def test_profile_modes():
    print("Testing profile mode switching...")

    if "test_modes" in _profiles:
        profile_unregister("test_modes")

    executed = []
    test_config = {
        "default": {"pop": ("default", lambda: executed.append("default"))},
        "combat": {"pop": ("combat", lambda: executed.append("combat"))},
    }

    profile_register("test_modes", test_config)

    # Should start in default
    assert profile_mode_get("test_modes") == "default", f"Failed: not in default mode"
    print("  ✓ Starts in default mode")

    profile_handle("test_modes", "pop")
    assert executed == ["default"], f"Failed: got {executed}"
    print("  ✓ Executes default mode action")

    # Switch to combat
    profile_mode_set("test_modes", "combat")
    assert profile_mode_get("test_modes") == "combat", f"Failed: not in combat mode"
    print("  ✓ Mode set works")

    executed.clear()
    profile_handle("test_modes", "pop")
    assert executed == ["combat"], f"Failed: got {executed}"
    print("  ✓ Executes combat mode action")

    # Cycle back to default
    next_mode = profile_mode_cycle("test_modes")
    assert next_mode == "default", f"Failed: got {next_mode}"
    print("  ✓ Mode cycle works")

    profile_unregister("test_modes")
    print()

def test_profile_get_legend():
    print("Testing profile_get_legend...")

    if "test_legend" in _profiles:
        profile_unregister("test_legend")

    test_config = {
        "default": {
            "pop": ("Click", lambda: None),
            "hiss:th_100": ("Scroll", lambda: None),
            "cluck": ("", lambda: None),  # Empty label, should be filtered
        },
    }

    profile_register("test_legend", test_config)

    legend = profile_get_legend("test_legend")
    assert legend.get("pop") == "Click", f"Failed: got {legend}"
    assert legend.get("hiss") == "Scroll", f"Failed: modifier not stripped, got {legend}"
    assert "cluck" not in legend, f"Failed: empty label not filtered, got {legend}"
    print("  ✓ Legend generated correctly")

    profile_unregister("test_legend")
    print()

def test_profile_events():
    print("Testing profile events...")

    if "test_events" in _profiles:
        profile_unregister("test_events")

    events = []
    def on_input(event: dict):
        events.append((event["input"], event["label"]))

    test_config = {
        "pop": ("Click", lambda: None),
    }

    profile_register("test_events", test_config)
    profile_event_register("test_events", on_input)

    profile_handle("test_events", "pop")
    assert len(events) == 1, f"Failed: event not triggered, got {events}"
    assert events[0] == ("pop", "Click"), f"Failed: wrong event data, got {events}"
    print("  ✓ Event callback triggered")

    # Unregister and verify no more events
    profile_event_unregister("test_events", on_input)
    events.clear()
    profile_handle("test_events", "pop")
    assert len(events) == 0, f"Failed: event still triggered after unregister, got {events}"
    print("  ✓ Event callback unregistered")

    profile_unregister("test_events")
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
        "pop": ("default pop", lambda: executed.append("default")),
    }

    input_map = InputMap()
    input_map.setup(test_config)

    # High power should match conditional
    input_map.execute("pop", power=15.0)
    assert executed == ["loud"], f"Failed: got {executed}"
    print("  ✓ conditional matches when condition is true")

    # Low power should fall through to default
    executed.clear()
    input_map.execute("pop", power=5.0)
    assert executed == ["default"], f"Failed: got {executed}"
    print("  ✓ falls through to unconditional default")

    print()

def test_input_map_conditional_missing_context():
    print("Testing InputMap conditional missing context...")

    executed = []
    test_config = {
        "pop:power>10": ("loud pop", lambda: executed.append("loud")),
        "pop": ("default pop", lambda: executed.append("default")),
    }

    input_map = InputMap()
    input_map.setup(test_config)

    # No power provided (None) should fall through to default
    input_map.execute("pop")
    assert executed == ["default"], f"Failed: got {executed}"
    print("  ✓ power=None falls through to default")

    print()

def test_input_map_conditional_multi_condition():
    print("Testing InputMap conditional multi-condition...")

    executed = []
    test_config = {
        "gaze:x<500:y<500": ("top-left", lambda: executed.append("top_left")),
        "gaze": ("default gaze", lambda: executed.append("default")),
    }

    input_map = InputMap()
    input_map.setup(test_config)

    input_map.execute("gaze", x=100.0, y=100.0)
    assert executed == ["top_left"], f"Failed: got {executed}"
    print("  ✓ x<500 AND y<500 matches")

    executed.clear()
    input_map.execute("gaze", x=600.0, y=100.0)
    assert executed == ["default"], f"Failed: got {executed}"
    print("  ✓ x>=500 falls through to default")

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

    # Same region — should suppress
    input_map.execute("gaze", x=200.0)
    assert executed == ["left"], f"Failed: should suppress, got {executed}"
    print("  ✓ Same region suppressed")

    # Transition to right region
    input_map.execute("gaze", x=600.0)
    assert executed == ["left", "right"], f"Failed: got {executed}"
    print("  ✓ Transition to right fires")

    # Same right region — suppress
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

    # Leave left (no condition matches) — else fires
    input_map.execute("gaze", x=600.0)
    assert executed == ["left", "neutral"], f"Failed: got {executed}"
    print("  ✓ Else fires on leaving region")

    # Stay in else — suppress
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

    # Switch mode — should reset active region
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
        "hiss:db_90": ("debounced scroll", lambda: executed.append("debounced")),
    }

    input_map = InputMap()
    input_map.setup(combat_input_map)

    # Both keys exist in the dict ("hiss:th_90" from spread, "hiss:db_90" from override)
    # Both resolve to base "hiss" — the last one processed should win
    input_map.execute("hiss")

    # The debounced one (last in dict) should win, but it's debounced so no immediate execution
    assert executed == [], f"Failed: debounce should delay execution, got {executed}"
    print("  ✓ Last modifier (db) wins over spread modifier (th)")

    actions.sleep("100ms")
    assert executed == ["debounced"], f"Failed: debounce didn't fire, got {executed}"
    print("  ✓ Debounced action fires after delay")

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

    # Switch to combat mode — override should be active
    input_map.setup_mode("combat")
    executed.clear()
    input_map.execute("hiss")
    assert executed == ["combat_scroll"], f"Failed: got {executed}"
    print("  ✓ Combat mode uses overridden action")

    # Wait for throttle to expire before switching back
    actions.sleep("100ms")

    # Switch back to default — should use default again
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
    assert legend == {"test_legend_s": "left click"}, f"Failed: got {legend}"
    print("  ✓ Returns {input: label}")

    legend2 = single_get_legend("test_legend_s", pop_map, "repeat")
    assert legend2 == {"test_legend_s": "repeat cmd"}, f"Failed: got {legend2}"
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

def test_profile_mode_revert():
    print("Testing profile_mode_revert...")

    if "test_revert_p" in _profiles:
        profile_unregister("test_revert_p")

    test_config = {
        "default": {"pop": ("default", lambda: None)},
        "combat": {"pop": ("combat", lambda: None)},
    }

    profile_register("test_revert_p", test_config)

    assert profile_mode_get("test_revert_p") == "default"
    profile_mode_set("test_revert_p", "combat")
    assert profile_mode_get("test_revert_p") == "combat"

    result = profile_mode_revert("test_revert_p")
    assert result == "default", f"Failed: got {result}"
    assert profile_mode_get("test_revert_p") == "default"
    print("  ✓ Reverts profile to previous mode")

    profile_unregister("test_revert_p")
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

def test_handle_bool_profile():
    print("Testing handle_bool profile...")

    if "test_bool_p" in _profiles:
        profile_unregister("test_bool_p")

    executed = []
    test_config = {
        "hiss": ("scroll", lambda: executed.append("start")),
        "hiss_stop": ("stop", lambda: executed.append("stop")),
    }

    profile_register("test_bool_p", test_config)

    profile_handle("test_bool_p", "hiss")
    assert executed == ["start"], f"Failed: got {executed}"

    profile_handle("test_bool_p", "hiss_stop")
    assert executed == ["start", "stop"], f"Failed: got {executed}"
    print("  ✓ Profile bool active/stop works")

    profile_unregister("test_bool_p")
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

    # Profile tests
    test_profile_register_unregister()
    test_profile_re_registration()
    test_profile_get()
    test_profile_handle()
    test_profile_modes()
    test_profile_get_legend()
    test_profile_events()

    # Single tests
    test_normalize_single_map_simple()
    test_normalize_single_map_tuple()
    test_normalize_single_map_expanded()
    test_single_handle_basic()
    test_single_handle_tuple()
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
    test_profile_mode_revert()

    # Bool handler tests
    test_handle_bool_basic()
    test_handle_bool_profile()
    test_handle_bool_single()

    print()
    print("=" * 50)
    print("All tests passed!")
    print("=" * 50)
