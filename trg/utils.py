from os import path
from gi.repository import GLib

_is_flatpak = None


def is_flatpak():
    global _is_flatpak
    if _is_flatpak is None:
        file_ = path.join(GLib.get_user_runtime_dir(), 'flatpak-info')
        _is_flatpak = path.exists(file_)
    return _is_flatpak
