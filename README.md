# Transmission Remote Gnome

Remote client for Transmission.

The goal of the project is to modernize [transmission-remote-gtk](https://github.com/transmission-remote-gtk/transmission-remote-gtk)
project in terms of UI and codebase. This is still a work in progress.

## Building

### Dependencies

- Meson >= 0.37.0 (build only)
- Python >= 3.4
- PyGObject
- GLib (Only 2.50+ tested)
- Gtk3 (Only 3.20+ tested)
- LibSoup


```sh
meson build
ninja -C build
sudo ninja -C build install
```
