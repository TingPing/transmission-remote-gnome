from os import path
from gi.repository import GLib

_is_flatpak = None


def is_flatpak():
    global _is_flatpak
    if _is_flatpak is None:
        _is_flatpak = path.exists('/.flatpak-info')
    return _is_flatpak
