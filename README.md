# montog - Monitor Toggle
Gnome app indicator tool to quickly toggle enabled monitor arrangements

https://github.com/sperry04/montog

Copyright (C) 2024 Scott Perry (sperry04)

Based loosely on monitor-switch by Rodrigo Silva (MestreLion)

## Caveats
* Developed and tested on Ubuntu 22.04 LTS / Gnome 42.9
* Uses `xrandr` for enabling/disabling monitors
* Only works with X11, Wayland is not supported

## Usage
Run from the command line with `$ montog.py` or `$ python3 montog.py`.

The montog menu will launch in the Gnome top bar.

### Arrangements
The menu consists of a list of monitor _arrangements_ that can be quickly toggled.  Arrangements are intended to represent:
* a set of enabled monitors 
* their order left-to-right (layouts with vertical components are not supported)
* and a designated primary monitor
so it's easy to directly select a specific layout with one click.

### Options
There are several options that may be toggled on the menu:
* _Auto-start on login_ - creates a `montog.desktop` file in `~/.config/autostart/` to automatically launch montog when you login
* _Install in apps_ - creates a `montog.desktop` file in `~/.local/share/applications/` to add to the applications launcher.

### About
The _About_ menu item opens a dialog with information about the system and application, including:
* The list of connected monitors as detected by `xrandr`
* The loaded (or auto-generated) configuration file
* Application version

### Quit
The _Quit_ menu exits the application

## Installation
Simply put the `montog.py` script wherever you keep your scripts.  Montog should run without any additional dependencies over the default Ubuntu Python 3.10 installation.

The first time you run montog, you can "install" it by checking the "Auto-start on login" and/or "Install in apps" menu options

## Uninstallation
* Either run montog and uncheck both installation options, or manually delete the `montog.desktop` files.
* Delete `montog.py` and any configuration files you do not wish to keep.

## Configuration
By default, montog will detect your connected (both enabled and disabled) monitors, including your primary monitor, and auto-generate a configuration for enabling all monitors, or each monitor singularly.  However, it cannot detect the correct left-to-right order for monitors that are disabled.

To properly configure montog, create a `montog-config.yaml` file in `~/.config/`, or in the same directory as `montog.py`.  An `example_montog-config.yaml` file is provided as a reference, and included in the documentation below.  The configuration file is loaded every time the menu is opened, so you may modify the file without needed to restart the application.  An illegal configuration file will cause the application to revert to the auto-generated configuration.

### Configuration File Format
The config file is standard YAML with two necessary blocks:
* `monitors` - Maps alias names to the monitor `id` and any additional `options` you wish to pass to `xrandr` when enabling the monitor, such as resolution, frame rate, etc.
* `arrangements` - Maps an arrangement name (which is used in the drop down menu) to a list of `enabled` monitor aliases (as defined in the `monitors` block) and a `primary` alias to indicate which monitor should be set as the primary.

### Configuration Example:
Note the use of unicode Emojis for iconography in the menu.

```YAML
# This example configuration file assumes a 3-monitor system with monitors 
# at ID's DP-0, DP-2, and DP-3 in that order, naming them with the aliases 
# "left", "center", and "right".
#
# It provides 5 arrangements for various 1, 2 or 3 enabled monitors, 
# preferring the center or left monitors as primary.  
#
# To use this configuration file, put it in ~/.config/ and edit the 
# monitors block to match the IDs show in the About dialog, paying attention
# to match the IDs with the positional alias names (left/center/right).
#
# Emojis are used in the arrangement names as iconography to make the menu
# clearer when switching active monitors.

# monitor aliases
#   maps alias name to monitor ID and any additional
#   xrandr options required by the monitor
monitors:
    left: 
        id: DP-0
        options: ""
    center:
        id: DP-2
        options: ""
    right:
        id: DP-4
        options: ""

# arrangements
#   maps arrangement name to list of enabled monitors
#   (in left-to-right order) and a primary monitor
arrangements:
    "🖥️ 🚫 🚫  Left":
        enabled: [ "left" ]
        primary: "left"
    "🖥️ 🖥️ 🚫  Left Two":
        enabled: [ "left", "center" ]
        primary: "center"
    "🖥️ 🖥️ 🖥️  All Monitors":
        enabled: [ "left", "center", "right" ]
        primary: "center"
    "🚫 🖥️ 🖥️  Right Two":
        enabled: [ "center", "right" ]
        primary: "center"
    "🚫 🚫 🖥️  Right":
        enabled: [ "right" ]
        primary: "right"
```
