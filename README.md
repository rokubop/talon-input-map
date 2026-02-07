![Version](https://img.shields.io/badge/version-0.6.0-blue)
![Status](https://img.shields.io/badge/status-preview-orange)

# Talon Input Map

![Preview](preview.svg)

This is an alternate way to define your noises, parrot, foot pedals, face gestures, or other input sources in a way that supports:
- combos
- mode switching
- throttling
- debounce
- variable inputs
- based on power, f0, f1, f2, x, y, or value

## Installation

Clone this repo into your [Talon](https://talonvoice.com/) user directory:

```sh
# mac and linux
cd ~/.talon/user

# windows
cd ~/AppData/Roaming/talon/user

git clone https://github.com/rokubop/talon-input-map/
```

## Usage

Your input looks like
```talon
parrot(pop): user.input_map_handle("pop")
```

Then in your actions, you define an input map that maps the "pop" input to a command:
```py
input_map = {
    "default": {
        "pop": ("click", lambda: actions.mouse_click(0)),
        "tut": ("cancel", lambda: actions.key("escape")),
        "tut tut": ("close window", lambda: actions.key("alt+f4")),
    },
    "repeat": {
        "pop": ("repeat", lambda: actions.core.repeat_command()),
        "tut": ("undo", lambda: actions.key("ctrl+z")),
        "tut tut": ("redo", lambda: actions.key("ctrl+shift+z")),
    },
}
```

And you return that input map in a context:
```py
@ctx.action_class("user")
class Actions:
    def input_map():
        return input_map
```

And you can switch between modes with
```py
actions.user.input_map_mode_set("default")
actions.user.input_map_mode_cycle()
```


## Example with Parrot

```talon
parrot(pop):                 user.input_map_handle("pop")
parrot(hiss):                user.input_map_handle("hiss")
parrot(hiss:stop):           user.input_map_handle("hiss_stop")
parrot(shush):               user.input_map_handle("shush")
parrot(shush:stop):          user.input_map_handle("shush_stop")
parrot(cluck):               user.input_map_handle("cluck")
```

## Example with Parrot (with context data)

Use `input_map_handle_parrot` to pass power and frequency data, enabling conditional matching:

```talon
parrot(pop):                 user.input_map_handle_parrot("pop", power, f0, f1, f2)
parrot(cluck):               user.input_map_handle_parrot("cluck", power, f0, f1, f2)
```

## Example with Gaze / XY Inputs

```talon
face(gaze_xy):               user.input_map_handle_xy("gaze", gaze_x, gaze_y)
gamepad(left_xy:repeat):     user.input_map_handle_xy("left_stick", left_x, left_y)
```

## Example with Boolean Inputs

```talon
face(dimple_left:change):    user.input_map_handle_value("dimple_left", value)
gamepad(l2:change):          user.input_map_handle_value("l2", value)
```

## Example with Foot Pedals

```talon
key(f13):                    user.input_map_handle("pedal_1")
key(f14):                    user.input_map_handle("pedal_2")
key(f15):                    user.input_map_handle("pedal_3")
```

## Configuration

```py
input_map = {
    "pop":         ("use", lambda: actions.user.game_key("e")),
    "cluck":       ("attack", lambda: actions.mouse_click(0)),
    "cluck cluck": ("hard attack", lambda: actions.mouse_click(1)),
    "cluck pop":   ("special", lambda: actions.mouse_click(2)),
    "hiss:db_100": ("jump", lambda: actions.user.game_key("space")),
    "hiss_stop":   ("", lambda: None),
    "shush:th_100":("crouch", lambda: actions.user.game_key("c")),
    "tut":         ("alt", lambda: actions.user.game_key("alt")),
    "tut ah":      ("turn left", actions.user.game_mouse_move_deg_left_90),
    "tut oh":      ("turn right", actions.user.game_mouse_move_deg_right_90),
    "tut guh":     ("turn around", actions.user.game_mouse_move_deg_180),
}

@ctx.action_class("user")
class Actions:
    def input_map():
        return input_map
```

## Define different modes:
```py
default_config = {
    "pop":         ("use", lambda: actions.user.game_key("e")),
    "cluck":       ("attack", lambda: actions.mouse_click(0)),
    "cluck cluck": ("hard attack", lambda: actions.mouse_click(1)),
    "cluck pop":   ("special", lambda: actions.mouse_click(2)),
    "hiss:db_100": ("jump", lambda: actions.user.game_key("space")),
    "hiss_stop":   ("", lambda: None),
    "shush:th_100":("crouch", lambda: actions.user.game_key("c")),
}
move_config = {
    **default_config,
    "pop":         ("left", lambda: actions.user.go_left()),
    "cluck":       ("right", lambda: actions.user.go_right()),
}
combat_config = {
    **default_config,
    "cluck":       ("attack", lambda: actions.mouse_click(0)),
    "cluck cluck": ("hard attack", lambda: actions.mouse_click(1)),
}

# Final config with each mode
input_map = {
    "default": default_config,
    "move": move_config,
    "combat": combat_config,
}

@ctx.action_class("user")
class Actions:
    def input_map():
        return input_map

# Actions
actions.user.input_map_mode_set("default")
actions.user.input_map_mode_cycle()
actions.user.input_map_mode_get()
```

## Variable Patterns
Use `$` to capture any primitive input in your pattern:

```py
input_map = {
    "tut $input": ("hold modifier", lambda input: actions.user.my_hold_command(input)),
    # Usage: "tut cluck", "tut hiss", "tut tut" etc.
}
```

## Conditional Matching
Branch on context values like power, frequency, or position. Requires using `input_map_handle_parrot`, `input_map_handle_xy`, or `input_map_handle_value` to pass context data.

```py
input_map = {
    # Branch on parrot power
    "pop:power>10":        ("loud pop", lambda: actions.user.loud_action()),
    "pop:power<=10":       ("soft pop", lambda: actions.user.soft_action()),

    # Branch on gaze position (multiple conditions = AND)
    "gaze:x<500:y<500":   ("top-left", lambda: actions.user.gaze_top_left()),
    "gaze":               ("default gaze", lambda: actions.user.gaze_default()),

    # Combine with throttle/debounce
    "pop:power>10:th_100": ("loud throttled", lambda: actions.user.loud_throttled()),
}
```

Supported context variables: `power`, `f0`, `f1`, `f2`, `x`, `y`, `value`

Supported operators: `>`, `<`, `>=`, `<=`, `==`, `!=`

Rules:
- Multiple conditions on the same input use AND logic
- First matching condition wins
- If no condition matches and an unconditional fallback exists, it executes
- If no condition matches and no fallback, silent no-op
- Missing context (e.g. `power=None`) causes the condition to fail

## Throttling
Throttling is useful when you have a continuous input, but you only want to trigger it once per 100ms for example:
```py
"shush:th_100":("jump", lambda: actions.user.game_key("space")),
```

## Debouncing
Debouncing on the start of a command means that you need to hold it for 100ms until it will trigger. You might want this if you also want to use normal english commands as well and don't want the input to be triggered immediately.
```py
"shush:db_100":("turn left", actions.user.game_mouse_move_continuous_left),
```

Debouncing at the stop of a command basically just means the stop will be delayed
```py
"shush_stop:db_100":("", actions.user.game_mouse_move_continuous_stop),
```

## Switching config dynamically
If you don't want to use modes, you can also swap out the input map on the fly, and it will automatically update.

```py
input_map = default_config

def use_other_config():
    global input_map
    input_map = other_config

@ctx.action_class("user")
class Actions:
    def input_map():
        return input_map
```

## Options:
| Definition | Description |
|------------|-------------|
| `"pop pop"` | Triggers when you combo two pops in a row within `300ms`. If you define this combo, then a regular `"pop"` will be delayed, in order to determine to use the single pop or wait for the combo pop. |
| `"pop cluck"` | Triggers when you combo pop then cluck within `300ms`. If you use this combo, then a regular `"pop"` will be delayed, in order to determine to use the single pop or wait for the pop+cluck. |
| `"pop cluck pop"` | Triggers when you combo pop then cluck then pop within `300ms` between each. If you use this combo, then a regular `"pop"` and `"pop cluck"` will be delayed, in order to determine to use the partial command or wait for the full potential combo. |
| `"pop:th_100"` | Throttles the pop command to only trigger once every 100ms. |
| `"pop:th"` | Default throttle for the pop command. |
| `"hiss:db_100"` | Debounces the hiss command to only trigger after 100ms of continuous input. |
| `"hiss:db"` | Default debounce for the hiss command. |
| `"pop $input"` | Variable pattern that captures any primitive input after "pop" and passes it to the lambda function. |
| `"pop:power>10"` | Conditional matching. Executes only when power > 10. Requires `input_map_handle_parrot`. |
| `"gaze:x<500:y<500"` | Multiple conditions (AND). Executes only when both x < 500 and y < 500. |
| `"pop:power>10:th_100"` | Conditional with throttle. Combines condition matching with throttling. |

## Testing

To run the test suite, open the Talon REPL and run:

```python
actions.user.input_map_test()
```

## Dependencies
none
