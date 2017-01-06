# Transmission Remote Gnome

Remote client for Transmission.

The goal of the project is to modernize [transmission-remote-gtk](https://github.com/transmission-remote-gtk/transmission-remote-gtk)
project in terms of UI and codebase. This is still a work in progress:

## TODO

- [x] Add Dialog
  - [x] Parse torrent files
  - [ ] Labels
- [x] Torrent List
  - [x] Sorting
  - [x] Filtering
    - [x] By status
    - [x] By tracker
    - [x] By directory
  - [x] Searching
  - [x] Right click actions
  - [ ] View/Edit properties
- [ ] Settings
  - [x] Local settings
  - [x] Dialog for configuration
  - [ ] Sync remote settings
- [ ] RPC Client
  - [x] Connecting
  - [x] Authentication
  - [x] Make fully Async
  - [ ] Better error handling
  - [ ] Full API coverage
- [x] Installation
  - [x] Misc files (desktop, appdata, translations)
  - [x] Icon
  - [x] Flatpak
- [x] Port build system to Meson

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
