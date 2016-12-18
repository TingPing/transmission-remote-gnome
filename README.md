# Transmission Remote Gnome

Remote client for Transmission.

The goal of the project is to modernize [transmission-remote-gtk](https://github.com/transmission-remote-gtk/transmission-remote-gtk)
project in terms of UI and codebase. This is still a work in progress:

## TODO

- [x] Add Dialog
  - [x] Parse torrent files
- [x] Torrent List
  - [x] Sorting
  - [x] Filtering
    - [x] By status
    - [ ] By tracker
    - [ ] By label/directory
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
  - [ ] Icon
  - [x] Flatpak
- [x] Port build system to Meson

## Building

```sh
meson build
ninja -C build
sudo ninja -C build install
```
