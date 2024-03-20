#!/usr/bin/python3
#
#   montog - Gnome App Indicator tool to quickly toggle enabled monitors
#
#   Copyright (C) 2024 Scott Perry (sperry04) https://github.com/sperry04
#
#   Based loosely on monitor-switch by Rodrigo Silva
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program. See <http://www.gnu.org/licenses/gpl.html>

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("AppIndicator3", "0.1")
from gi.repository import Gtk
from gi.repository import AppIndicator3 as appindicator

from typing import Union
import subprocess
import yaml
import os


app_name = "montog"
app_desc = "Monitor Toggle: quickly switch active monitor arrangement"
app_version = "0.1"
home_dir = os.path.expanduser("~")
config_filenames = [f"{home_dir}/.config/{app_name}-config.yaml", f"./{app_name}-config.yaml"]
autostart_filename = f"{home_dir}/.config/autostart/{app_name}.desktop"
install_filename = f"{home_dir}/.local/share/applications/{app_name}.desktop"
desktop_file_contents = f"""[Desktop Entry]
Name={app_name}
Version={app_version}
GenericName={app_name}
Comment={app_desc}
Exec={os.path.realpath(__file__)}
Terminal=false
Type=Application
Icon=monitor
"""


def show_modal_dialog(text, title=None) -> Gtk.ResponseType:
    """
    Displays a modal dialog box that can contain arbitrary monospaced text
    """
    # Create the dialog to show
    dialog = Gtk.Dialog()
    dialog.set_default_size(800, 600)
    dialog.set_title(f"{app_name} - v{app_version}" + ("" if title is None else f": {title}"))
    dialog.set_modal(True)

    # Create a text view with monospaced font
    textview = Gtk.TextView()
    textview.set_editable(False)
    textview.set_cursor_visible(False)
    textview.set_wrap_mode(Gtk.WrapMode.WORD)
    textview.set_monospace(True)

    # Insert text into the text view
    buffer = textview.get_buffer()
    buffer.set_text(text)

    # Create a scrolled window to contain the text view
    scrolled_window = Gtk.ScrolledWindow()
    scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
    scrolled_window.add(textview)

    # Create a box to hold the scrolled window
    thickness = 20
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=thickness)
    box.set_margin_top(thickness)
    box.set_margin_bottom(thickness)
    box.set_margin_start(thickness)
    box.set_margin_end(thickness)

    # Add the scrolled window to the box
    box.pack_start(scrolled_window, expand=True, fill=True, padding=0)

    # Add the scrolled window to the dialog content area
    dialog.vbox.pack_start(box, expand=True, fill=True, padding=0)

    # Add an "Ok" button
    dialog.add_button(Gtk.STOCK_OK, Gtk.ResponseType.OK)

    # Show the dialog and wait for response
    dialog.show_all()
    rval = dialog.run()
    dialog.destroy()
    return rval


def get_connected_monitors() -> list:
    """
    Uses xrandr to get a list of connected monitor IDs
    """
    try:
        rval = []

        # Run the xrandr --listmonitors command to get the enabled monitors
        for line in subprocess.check_output(["xrandr", "--listmonitors"], text=True).strip().splitlines()[1:]:
            # Extract monitor name and position information
            parts = line.strip().split()
            rval.append({"id": parts[3], "pos": parts[2].split("+")[-2], "enabled": True, "primary": parts[1].startswith("+*")})

        # sort the enabled monitors by position
        rval = sorted(rval, key=lambda monitor: monitor["pos"])

        # Run xrandr command to get disabled monitors
        for line in subprocess.check_output(["xrandr"], text=True).strip().splitlines():
            # Check if the line contains information about a connected monitor
            if " connected" in line:
                mid = line.split()[0]
                if mid not in [monitor["id"] for monitor in rval]:
                    rval.append({"id": mid, "pos": None, "enabled": False, "primary": False})
        return rval
    except subprocess.CalledProcessError as ex:
        print(f"Error running xrandr: {ex}")
        return []


def read_config() -> dict:
    """
    Reads the config file, looking in multiple places before using a default config based
    on detected monitors, returns the loaded config data
    """
    rval = None
    for filename in config_filenames:
        try:
            with open(filename) as f:
                rval = yaml.safe_load(f)
                rval["file"] = filename
                break  # no need to try the next filename
        except Exception as ex:
            print(f"Error loading '{filename}': {ex}")
            continue  # try the next filename
    if rval is None:
        # we never found a config file, use the connected monitors to make one up
        # monitors = {monitor.get("id"): {"id": monitor.get("id"), "options": ""} for monitor in get_connected_monitors()}
        monitors = get_connected_monitors()
        rval = {
            "monitors": {monitor.get("id"): {"id": monitor.get("id"), "options": ""} for monitor in monitors},
            "arrangements": {
                ("🖥️ " * len(monitors))
                + "All Monitors": {
                    "enabled": [monitor.get("id") for monitor in monitors],
                    "primary": next(monitor.get("id") for monitor in monitors if monitor.get("primary", False)),
                }
            },
            "file": f"This is an auto-generated configuration, please create your own config file at {config_filenames[0]}",
        }
        for monitor in monitors:
            rval["arrangements"].update({"🖥️ " + monitor.get("id"): {"enabled": [monitor.get("id")], "primary": monitor.get("id")}})
    return rval


def on_menu_show(menu) -> None:
    """
    Handler called just before the app indicator menu is shown,
    updates the menu with the arrangements from the current config
    """
    config = read_config()

    menu.foreach(lambda menu_item: menu.remove(menu_item))

    for arrangement in config.get("arrangements", {}).keys():
        menu_item = Gtk.MenuItem(label=arrangement)
        menu_item.connect("activate", on_menu_arrange)
        menu.append(menu_item)

    menu.append(Gtk.SeparatorMenuItem())

    toggle_menu_item = Gtk.CheckMenuItem(label="Auto-start on login")
    toggle_menu_item.connect("toggled", on_toggle_auto_start)
    toggle_menu_item.set_active(os.path.exists(autostart_filename))
    menu.append(toggle_menu_item)

    toggle_menu_item = Gtk.CheckMenuItem(label="Install in apps")
    toggle_menu_item.connect("toggled", on_toggle_install)
    toggle_menu_item.set_active(os.path.exists(install_filename))
    menu.append(toggle_menu_item)

    menu.append(Gtk.SeparatorMenuItem())

    info_menu_item = Gtk.MenuItem(label="About")
    info_menu_item.connect("activate", on_menu_about)
    menu.append(info_menu_item)

    quit_menu_item = Gtk.MenuItem(label="Quit")
    quit_menu_item.connect("activate", on_menu_quit)
    menu.append(quit_menu_item)

    menu.show_all()


def on_menu_arrange(item) -> None:
    """
    Handler called when an arrangement is selected,
    calls xrandr to activate the configured monitors
    """
    config = read_config()
    xrandr = ["xrandr"]
    arrangement = config.get("arrangements", {}).get(item.get_label(), {})

    # turn off all the disabled monitors
    for alias, monitor in config.get("monitors", {}).items():
        if alias not in arrangement.get("enabled", []):
            xrandr.extend(["--output", monitor.get("id", "unknown_id"), "--off"])

    # turn on the enabled monitors
    last_mid = None
    for alias in arrangement.get("enabled", []):
        mid = config.get("monitors", {}).get(alias, {}).get("id", "unknown_id")
        xrandr.extend(["--output", mid, "--auto"])
        options = config.get("monitors", {}).get(alias, {}).get("options", "")
        if options:
            xrandr.extend(options.split())
        if last_mid is None:
            xrandr.extend(["--pos", "0x0"])
        else:
            xrandr.extend(["--right-of", last_mid])
        last_mid = mid
        if alias == arrangement["primary"]:
            xrandr.extend(["--primary"])

    if last_mid is None:
        print("This arrangement would result in no enabled monitors! Aborting.")
        return

    try:
        # Run xrandr command to set active displays
        if True or show_modal_dialog(" ".join(xrandr), "Confirm?") == Gtk.ResponseType.OK:
            subprocess.check_call(xrandr)

    except subprocess.CalledProcessError as ex:
        # Handle any errors that occur when running the xrandr command
        print(f"Error running xrandr: {ex}")


def on_toggle_auto_start(item) -> None:
    if item.get_active():
        if not os.path.exists(autostart_filename):
            try:
                dir = os.path.dirname(autostart_filename)
                if not os.path.exists(dir):
                    os.makedirs(dir)
                with open(autostart_filename, "w") as file:
                    file.write(desktop_file_contents)
                # os.chmod(desktop_filename, 0o755)
            except Exception as ex:
                print(f"Error writing desktop file: {ex}")
    else:
        if os.path.exists(autostart_filename):
            try:
                os.remove(autostart_filename)
            except OSError as ex:
                print(f"Error removing desktop file: {ex}")


def on_toggle_install(item) -> None:
    if item.get_active():
        if not os.path.exists(install_filename):
            try:
                dir = os.path.dirname(install_filename)
                if not os.path.exists(dir):
                    os.makedirs(dir)
                with open(install_filename, "w") as file:
                    file.write(desktop_file_contents)
                # os.chmod(desktop_filename, 0o755)
            except Exception as ex:
                print(f"Error writing desktop file: {ex}")
    else:
        if os.path.exists(install_filename):
            try:
                os.remove(install_filename)
            except OSError as ex:
                print(f"Error removing desktop file: {ex}")


def on_menu_about(item) -> None:
    """
    Handler for the about menu,
    displays the dialog with various information about the app/system
    """
    config = read_config()

    config_text = (
        yaml.safe_dump(
            {"monitors": config.get("monitors", []), "arrangements": config.get("arrangements", [])},
            indent=8,
            sort_keys=False,
            allow_unicode=True,
        )
        .replace(
            "monitors:",
            "\n    # monitor aliases\n    #   maps alias name to monitor ID and any additional\n    #   xrandr options required by the monitor\n    monitors:",
        )
        .replace(
            "arrangements:",
            "\n    # arrangements\n    #   maps arrangement name to list of enabled monitors\n    #   (in left-to-right order) and a primary monitor\n    arrangements:",
        )
    )

    show_modal_dialog(
        f"""-----------------------------------------------------------
{app_name} v{app_version}
{app_desc}
-----------------------------------------------------------

Monitors detected by xrandr:
{yaml.safe_dump(get_connected_monitors(), indent=4, sort_keys=False, allow_unicode=True)}

Configuration ({config.get("file", "unknown config file")}):
{config_text}
""",
        "About",
    )


def on_menu_quit(item) -> None:
    """
    Handler for the quit menu,
    exits the app
    """
    Gtk.main_quit()


def main() -> None:
    """
    Main application entry point
    """
    indicator = appindicator.Indicator.new(app_name, "monitor", appindicator.IndicatorCategory.HARDWARE)
    indicator.set_status(appindicator.IndicatorStatus.ACTIVE)

    menu = Gtk.Menu()

    menu.connect("show", on_menu_show)
    indicator.set_menu(menu)
    Gtk.main()


if __name__ == "__main__":
    main()
