# torrent_list_view.py
#
# Copyright (C) 2016 Patrick Griffis <tingping@tingping.se>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from enum import IntEnum
from collections import (OrderedDict, namedtuple)
from functools import partial
from gettext import gettext as _

from gi.repository import (
    GLib,
    GObject,
    Gio,
    Gdk,
    Gtk,
)

# This import is used by the UI file indirectly
# noinspection PyUnresolvedReferences
from . import cell_renderers # noqa: ignore=F401
from .client import Client
from .add_dialog import MoveDialog
from .list_wrapper import WrappedStore
from .torrent_properties import TorrentProperties
from .utils import is_flatpak
from .gi_composites import GtkTemplate


@GtkTemplate(ui='/se/tingping/Trg/ui/torrentview.ui')
class TorrentListView(Gtk.TreeView):
    __gtype_name__ = 'TorrentListView'

    client = GObject.Property(type=Client, flags=GObject.ParamFlags.READWRITE|GObject.ParamFlags.CONSTRUCT_ONLY)

    def __init__(self, model, **kwargs):
        # NOTE: Order must match TorrentColumn enum
        props = OrderedDict()
        props['name'] = str
        props['size-when-done'] = GObject.TYPE_UINT64
        props['percent-done'] = float
        props['rate-download'] = GObject.TYPE_UINT64
        props['rate-upload'] = GObject.TYPE_UINT64
        props['status'] = GObject.TYPE_UINT64
        props['download-dir'] = str
        props['error'] = GObject.TYPE_UINT64
        store = WrappedStore.new_for_model(model, props)
        self.filter_model = Gtk.TreeModelFilter(child_model=store)
        self._sort_model = Gtk.TreeModelSort(model=self.filter_model)

        super().__init__(model=self._sort_model, **kwargs)
        self.init_template()

    def do_button_press_event(self, event: Gdk.EventButton) -> int:
        if not event.triggers_context_menu():
            return Gtk.TreeView.do_button_press_event(self, event)

        ret = self.get_path_at_pos(event.x, event.y)
        if not ret or not ret[0]:
            return Gdk.EVENT_STOP

        # If we right click a single unselcted item, select it.
        path = ret[0]
        selection = self.get_selection()
        if not selection.path_is_selected(path):
            selection.unselect_all()
            selection.select_path(path)

        # But we handle multple selections
        model, paths = selection.get_selected_rows()
        torrents = []
        for path in paths:
            it = model.get_iter(path)
            torrent = model[it][-1]
            torrents.append(torrent)

        menu = self._build_menu(torrents)
        menu.popup_at_pointer(event)
        return Gdk.EVENT_STOP

    def _open_torrent_properties(self, torrents):
        for torrent in torrents:  # TODO: Handle opening too many
            dialog = TorrentProperties(torrent=torrent, client=self.client, transient_for=self.get_toplevel())
            dialog.present()

    def _move_torrents(self, torrents):
        for torrent in torrents:  # TODO: Maybe move multiple at once?
            dialog = MoveDialog(torrent=torrent, client=self.client, transient_for=self.get_toplevel())
            dialog.present()

    def _open_torrents(self, torrents):
        for torrent in torrents:
            Gtk.show_uri_on_window(self.get_toplevel(), torrent.uri, Gdk.CURRENT_TIME)

    def _delete_torrents(self, torrents):
        def response(dialog, response_id):
            if response_id == Gtk.ResponseType.OK:
                self.client.torrent_remove(torrents, True)
            if response_id != Gtk.ResponseType.DELETE_EVENT:
                dialog.destroy()

        text = GLib.markup_escape_text(_('Remove Torrent and Data?'))
        dialog = Gtk.MessageDialog(transient_for=self.get_toplevel(),
                                   destroy_with_parent=True,
                                   message_type=Gtk.MessageType.QUESTION,
                                   buttons=Gtk.ButtonsType.OK_CANCEL,
                                   use_markup=True,
                                   text='<b>{}</b>'.format(text))
        dialog.connect('response', response)
        dialog.present()

    def _build_menu(self, torrents) -> Gio.Menu:
        Entry = namedtuple('Entry', ['label', 'function'])

        MENU_ITEMS = [
            Entry(_('Resume'), partial(self.client.torrent_start, torrents)),
            Entry(_('Pause'), partial(self.client.torrent_stop, torrents)),
            Entry(_('Verify'), partial(self.client.torrent_verify, torrents)),
            (),
            Entry(_('Move'), partial(self._move_torrents, torrents)),
            Entry(_('Remove'), partial(self.client.torrent_remove, torrents)),
            Entry(_('Delete'), partial(self._delete_torrents, torrents)),
            (),
            Entry(_('Properties'), partial(self._open_torrent_properties, torrents)),
        ]

        # TODO: It can work in flatpak depending in permissions
        if self.client.is_local and not is_flatpak():
            open_entry = Entry(_('Open'), partial(self._open_torrents, torrents))
            MENU_ITEMS.insert(4, tuple())
            MENU_ITEMS.insert(4, open_entry)

        def on_activate(widget, callback):
            callback()
            self.client.refresh()

        menu = Gtk.Menu.new()
        for entry in MENU_ITEMS:
            if entry:
                item = Gtk.MenuItem.new_with_label(entry.label)
                if entry.function:
                    item.connect('activate', on_activate, entry.function)
            else:
                item = Gtk.SeparatorMenuItem.new()
            item.show()
            menu.append(item)

        menu.attach_to_widget(self)
        menu.show()
        return menu


class TorrentColumn(IntEnum):
    name = 0
    size = 1
    progress = 2
    down = 3
    up = 4
    status = 5
    directory = 6
    error = 7
