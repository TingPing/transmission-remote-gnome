# Transmission Remote Gnome

Remote client for Transmission.

The goal of the project is to modernize [transmission-remote-gtk](https://github.com/transmission-remote-gtk/transmission-remote-gtk)
project in terms of UI and codebase. This is still a work in progress:

## TODO

- [x] Add Dialog
  - [x] Parse torrent files
- [ ] Torrent List
  - [ ] Sorting
  - [ ] Filtering
  - [ ] Right click options
  - [ ] View properties
- [ ] Settings
  - [x] Local settings
  - [ ] Dialog for configuration
  - [ ] Sync remote settings
- [ ] RPC Client
  - [x] Connecting
  - [x] Authentication
  - [ ] Make fully Async
  - [ ] Better error handling
  - [ ] Full API coverage
- [ ] Misc files (desktop, appdata, icons)

## Building

```sh
./autogen.sh
make -s
make run
# Installing is not yet supported
```
