from .input_map import (
    get_base_input,
    extract_variables,
    pattern_to_regex,
    match_variable_pattern,
    has_variables,
    validate_variable_action,
)

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

def run_tests():
    print("=" * 50)
    print("Running Input Map Tests")
    print("=" * 50)
    print()

    test_get_base_input()
    test_has_variables()
    test_extract_variables()
    test_pattern_to_regex()
    test_match_variable_pattern()
    test_validate_variable_action()

    print("=" * 50)
    print("All tests passed!")
    print("=" * 50)
