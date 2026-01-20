# Input Map

![Version](https://img.shields.io/badge/version-0.6.0-blue)
![Status](https://img.shields.io/badge/status-preview-orange)

This is an alternate way to define your noises, parrot, foot pedals, face gestures, or other input sources in a way that supports:
- sequential combos
- concurrent inputs
- throttling
- debounce
- modes for groups of input maps
- tags for groups of input maps
- variable patterns with $variable syntax

Combos have a timeout of `300ms`. If you define a combo, then the first input will no longer fire immediately, but only after `300ms`.

## Installation

Clone this repo into your [Talon](https://talonvoice.com/) user directory:

```sh
# mac and linux
cd ~/.talon/user

# windows
cd ~/AppData/Roaming/talon/user

git clone https://github.com/rokubop/talon-input-map/
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

## Testing

To run the test suite, open the Talon REPL and run:

```python
actions.user.input_map_test()
```

## Dependencies
none
