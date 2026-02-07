from talon import actions
from .input_map import InputMap
from .input_map_parse import (
    get_base_input,
    extract_variables,
    pattern_to_regex,
    match_variable_pattern,
    has_variables,
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
    profile_get_legend,
    profile_event_register,
    profile_event_unregister,
    _profiles,
    _profile_callbacks,
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
    def on_input(input: str, label: str):
        events.append((input, label))

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

    # Profile tests
    test_profile_register_unregister()
    test_profile_re_registration()
    test_profile_get()
    test_profile_handle()
    test_profile_modes()
    test_profile_get_legend()
    test_profile_events()

    print()
    print("=" * 50)
    print("All tests passed!")
    print("=" * 50)
