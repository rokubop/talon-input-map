![Version](https://img.shields.io/badge/version-0.6.0-blue)
![Status](https://img.shields.io/badge/status-experimental-orange)
![License](https://img.shields.io/badge/license-MIT-green)

# Talon Input Map

![Preview](preview.svg)

This is an alternate way to define your noises, parrot, foot pedals, face gestures, or other input sources in a way that supports:
- combos
- mode switching
- throttling
- debounce
- variable inputs
- greater than or less than for `power`, `f0`, `f1`, `f2`, `x`, `y`, or `value`

## Installation

Clone this repo into your [Talon](https://talonvoice.com/) user directory:

```sh
# mac and linux
cd ~/.talon/user

# windows
cd ~/AppData/Roaming/talon/user

git clone https://github.com/rokubop/talon-input-map/
```

## Table of Contents
- [Talon Input Map](#talon-input-map)
  - [Installation](#installation)
  - [Table of Contents](#table-of-contents)
  - [Usage - simple](#usage---simple)
  - [Usage - all features + modes](#usage---all-features--modes)
  - [Profiles - multiple input maps at the same time](#profiles---multiple-input-maps-at-the-same-time)
  - [Options:](#options)
  - [Testing](#testing)
  - [Dependencies](#dependencies)

## Usage - simple

1. Call `user.input_map_handle` from a talon file.
    ```talon
    parrot(pop): user.input_map_handle("pop")
    ```

2. Define your input map in a python file and return it in a context action.
    ```py
    input_map = {
        "pop": ("click", lambda: actions.mouse_click(0)),
        "tut": ("cancel", lambda: actions.key("escape")),
        "tut tut": ("close window", lambda: actions.key("alt+f4")),
    }
    ```

3. Pass that input map to the context action:
    ```py
    @ctx.action_class("user")
    class Actions:
        def input_map():
            return input_map
    ```

## Usage - all features + modes

1. Wire up your inputs in a talon file. Use the handler that matches your input source:

    ```talon
    parrot(pop):                 user.input_map_handle_parrot("pop", power, f0, f1, f2)
    parrot(cluck):               user.input_map_handle("cluck")
    parrot(tut):                 user.input_map_handle("tut")
    parrot(hiss):                user.input_map_handle("hiss")
    parrot(hiss:stop):           user.input_map_handle("hiss_stop")
    face(gaze_xy):               user.input_map_handle_xy("gaze", gaze_x, gaze_y)
    face(dimple_left:change):    user.input_map_handle_value("dimple_left", value)
    ```

    - `input_map_handle` - generic handler - works for everything
    - `input_map_handle_parrot` - if you want to use `power`, `f0`, `f1`, `f2`
    - `input_map_handle_xy` - if you want to use `x` or `y` (for gaze or gamepad sticks)
    - `input_map_handle_value` - if you want to use `value` (for face features or gamepad triggers using `:change`)

2. Define your input map with modes:

    ```py
    # my_game.py
    default_input_map = {
        "cluck":                 ("attack", lambda: actions.mouse_click(0)),
        "cluck cluck":           ("hard attack", lambda: actions.mouse_click(1)),
        "cluck pop":             ("special", lambda: actions.mouse_click(2)),
        "hiss:th_90":            ("scroll", lambda: actions.user.scroll_down()),
        "hiss_stop:db_100":      ("", lambda: None),
        "tut $noise":            ("reverse", lambda noise: actions.user.reverse(noise)),
        "pop:power>10":          ("loud click", lambda: actions.user.strong_click()),
        "pop:power<=10":         ("soft click", lambda: actions.mouse_click(0)),
        "gaze:x<-0.5":           ("look left", lambda x, y: actions.user.aim_left(x, y)),
        "gaze:x>0.5":            ("look right", lambda x, y: actions.user.aim_right(x, y)),
        "gaze:else":             ("neutral", lambda: actions.user.aim_reset()),
        "dimple_left:value>0.5": ("ability on", lambda: actions.user.activate()),
        "dimple_left:else":      ("ability off", lambda: actions.user.deactivate()),
    }

    combat_input_map = {
        **default_input_map,
        "cluck":                 ("block", lambda: actions.user.game_key("q")),
        "cluck cluck":           ("parry", lambda: actions.user.game_key("e")),
        "pop:power>10":          ("heavy strike", lambda: actions.user.heavy_strike()),
        "pop:power<=10":         ("quick jab", lambda: actions.user.quick_jab()),
    }

    input_map = {
        "default": default_input_map,
        "combat": combat_input_map,
    }

    @ctx.action_class("user")
    class Actions:
        def input_map():
            return input_map
    ```

3. Switch modes:
    ```py
    actions.user.input_map_mode_set("combat")
    actions.user.input_map_mode_cycle()
    ```

Key behaviors:
- **Combos** - defining `"cluck cluck"` delays single `"cluck"` to wait for a potential second input
- **Throttle/debounce** - `hiss:th_90` triggers at most once per 90ms, `hiss_stop:db_100` delays the stop by 100ms
- **Variable pattern** - `"tut $noise"` captures the next input and passes it to the lambda
- **Conditions without `else`** (pop) - fires every event while the condition is true
- **Conditions with `else`** (gaze, dimple_left) - fires once on entering a region, suppressed until region changes
- **Context params** - `lambda x, y:` receives current values at fire time
- **Continuous pairs** - `"hiss"` / `"hiss_stop"` map start and end of a held noise
- **Mode spread** - `{**default_input_map, ...}` inherits everything, override only what changes

## Profiles - multiple input maps at the same time

Instead of the context approach, you can use profiles to have multiple input maps active at the same time. Each profile is registered by name and managed independently.

1. Register profiles from a python file:
    ```py
    navigation_map = {
        "pop": ("select", lambda: actions.mouse_click(0)),
        "hiss:th_100": ("scroll", lambda: actions.user.scroll_down()),
    }
    combat_map = {
        "cluck": ("attack", lambda: actions.mouse_click(0)),
        "cluck cluck": ("heavy attack", lambda: actions.mouse_click(1)),
    }

    actions.user.input_map_profile_register("navigation", navigation_map)
    actions.user.input_map_profile_register("combat", combat_map)
    ```

2. Route inputs to profiles from a talon file:
    ```talon
    parrot(pop):        user.input_map_profile_handle("navigation", "pop")
    parrot(hiss):       user.input_map_profile_handle("navigation", "hiss")
    parrot(cluck):      user.input_map_profile_handle("combat", "cluck")
    ```

3. Profiles support modes, events, and all the same features:
    ```py
    actions.user.input_map_profile_mode_set("combat", "defensive")
    actions.user.input_map_profile_mode_cycle("combat")
    actions.user.input_map_profile_event_register("combat", on_input)
    actions.user.input_map_profile_unregister("combat")
    ```

## Options:
| Definition | Description |
|------------|-------------|
| `"pop cluck"` | Combo. Triggers within `300ms` window. Shorter matches are delayed to wait for longer combos. |
| `"pop:th_100"` | Throttle. Triggers once per `100`ms. `":th"` for default. |
| `"hiss:db_100"` | Debounce. Triggers after `100`ms of continuous input. `":db"` for default. |
| `"pop $input"` | Variable pattern. Captures input and passes it to the lambda. |
| `"pop:power>10"` | Condition. Fires only when `power > 10`. Variables: `power`, `f0`, `f1`, `f2`, `x`, `y`, `value`. Operators: `>`, `<`, `>=`, `<=`, `==`, `!=`. |
| `"gaze:x<500:y<500"` | Multiple conditions (AND). |
| `"gaze:else"` | Edge-triggered. Adding `else` makes conditions fire once per region transition instead of every event. |
| `"pop:power>10:th_100"` | Modifiers compose. Conditions, throttle, and debounce can be combined. |

## Testing

To run the test suite, open the Talon REPL and run:

```python
actions.user.input_map_tests()
```

## Dependencies
none
