# Plan: Conditional Input Matching

## File Structure

- `input_map.py` — runtime/hot path (InputMap class, execute, throttle/debounce, events)
- `input_map_parse.py` — parsing/cold path (condition parsing, validation, categorization)

Conditional parsing and validation goes in `input_map_parse.py`.
Condition evaluation at runtime stays in `input_map.py`.

---

## Overview

Add support for conditions on input keys based on input context (power, x, y, value, etc.)

```python
input_map = {
    "pop:power>10":       ("loud pop", loud_action),
    "pop:power<=10":      ("soft pop", soft_action),
    "dimple_left:value>0.4": ("dimple triggered", dimple_action),
    "gaze:x<500:y<500:db_100": ("top-left gaze", gaze_action),
}
```

---

## Syntax

### Condition format
```
input:param<op>value
```

- `param`: one of `power`, `f0`, `f1`, `f2`, `x`, `y`, `value`
- `op`: `>`, `<`, `>=`, `<=`, `==`, `!=`
- `value`: number (int or float like `0.4`, `10`, `500`)

### Multiple conditions (AND)
```
gaze:x<500:y<500
```

### Combined with existing modifiers
```
gaze:x<500:y<500:db_100    # conditions + debounce
pop:power>10:th_90         # condition + throttle
```

---

## Implementation Steps

### 1. Parse conditions in `get_modified_action` or new function

Extract conditions from input key:
```python
"pop:power>10:th_90" -> {
    "base_input": "pop",
    "conditions": [("power", ">", 10)],
    "modifiers": {"throttle": 90}
}
```

Regex pattern for conditions:
```python
r':(power|f0|f1|f2|x|y|value)(>|<|>=|<=|==|!=)(-?\d+\.?\d*)'
```

### 2. Store conditions with categorized commands

Current structure:
```python
immediate_commands = {
    "pop": (label, action_func)
}
```

New structure:
```python
immediate_commands = {
    "pop": [
        {"conditions": [("power", ">", 10)], "label": "loud", "action": func1},
        {"conditions": [("power", "<=", 10)], "label": "soft", "action": func2},
        {"conditions": [], "label": "default", "action": func3},  # no condition
    ]
}
```

Or keep separate:
```python
immediate_commands = {"pop": (label, action)}  # unconditional
conditional_commands = {
    "pop": [
        {"conditions": [...], "label": ..., "action": ...},
    ]
}
```

### 3. Evaluate conditions at execute time

```python
def evaluate_condition(condition, context):
    param, op, value = condition
    actual = context.get(param)
    if actual is None:
        return False  # or raise?

    ops = {
        ">": lambda a, b: a > b,
        "<": lambda a, b: a < b,
        ">=": lambda a, b: a >= b,
        "<=": lambda a, b: a <= b,
        "==": lambda a, b: a == b,
        "!=": lambda a, b: a != b,
    }
    return ops[op](actual, value)

def evaluate_conditions(conditions, context):
    return all(evaluate_condition(c, context) for c in conditions)
```

### 4. Modify execute() to check conditions

In `execute()`:
1. Build context dict from stored `last_*` values
2. When matching input, check conditional commands first
3. Find first matching condition set (or most specific?)
4. Fall through to unconditional if no conditions match

### 5. Handle combos with conditions

For `"tut pop:power>10"`:
- Parse as combo `["tut", "pop"]` with condition on `"pop"`
- Condition evaluated when `pop` arrives (last input in chain)
- Store condition with the combo entry

---

## Decisions

### Validation
- **All validation at setup time** — strict, error early on malformed/ambiguous
- **No runtime validation** — keep hot path fast

### Precedence
- **Overlapping conditions = error at setup**
- User must define mutually exclusive conditions (e.g., `>10` and `<=10`, not `>5` and `>10`)

### Fallback
- If no condition matches, **no action** (silent)
- User can define explicit fallback with plain `pop` alongside `pop:power>10`

### Missing context
- If condition references `power` but power=None: **condition fails** (doesn't match)
- No error, no warning — just doesn't match

### Condition logic
- Multiple conditions = **AND**
- No OR support (keep it simple)

### Combos
- `"tut pop:power>10"` — condition evaluated when combo completes
- Context from the final input in the chain

### Variable patterns
- `"tut $input:power>10"` — condition applies to the pattern match
- Evaluated with context from the triggering input

---

## Performance Considerations

- Condition parsing: Once at setup, not hot path
- Condition evaluation: Per-execute, but simple comparisons (~10-50ns each)
- Multiple condition entries: Need to iterate candidates, but likely few per input
- Store context: Already doing this (7 assignments per call)

**Estimated overhead:** Minimal if conditions are optional and most inputs don't use them.

---

## Testing

- Single condition: `pop:power>10`
- Multiple conditions: `gaze:x<500:y<500`
- Combined with throttle/debounce: `pop:power>10:th_90`
- Combo with condition: `tut pop:power>10`
- Fallback to unconditional
- Missing context handling
- Edge cases: boundary values, negative numbers, floats
