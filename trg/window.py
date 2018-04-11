# window.py
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

import logging
from collections import namedtuple
from contextlib import suppress
from functools import lru_cache
from urllib.parse import urlparse

from gi.repository import (
    GLib,
    GObject,
    Gio,
    Gdk,
    Gtk,
)

from .list_model_override import ListStore
from .gi_composites import GtkTemplate
from .torrent_list_view import TorrentListView, TorrentColumn
from .add_dialog import AddDialog, AddURIDialog
from .client import Client
from .torrent import TorrentStatus


@GtkTemplate(ui='/se/tingping/Trg/ui/applicationwindow.ui')
class ApplicationWindow(Gtk.ApplicationWindow):
    __gtype_name__ = 'ApplicationWindow'

    client = GObject.Property(type=Client)
    main_box = GtkTemplate.Child()
    search_entry = GtkTemplate.Child()
    search_revealer = GtkTemplate.Child()
    header_bar = GtkTemplate.Child()
    alt_speed_toggle = GtkTemplate.Child()
    tracker_box = GtkTemplate.Child()
    directory_box = GtkTemplate.Child()
    main_stack = GtkTemplate.Child()
    warning_page = GtkTemplate.Child()
    main_sw = GtkTemplate.Child()
    no_torrents = GtkTemplate.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.init_template()
        self._init_actions()
        self._filter = None
        self._filter_text = None
        self._filter_tracker = None
        self._filter_directory = None
        self._add_dialogs = []
        self._queued_torrents = []

        self._hooks = [
            self.client.connect('notify::download-speed', self._on_speed_refresh),
            self.client.connect('notify::connected', self._on_connected_change),
        ]
        self.client.bind_property('alt-speed-enabled', self.alt_speed_toggle,
                                  'active', GObject.BindingFlags.SYNC_CREATE)

        # Set initial state
        self._on_connected_change()
        self._on_speed_refresh()

        torrent_target = Gtk.TargetEntry.new('text/uri-list', Gtk.TargetFlags.OTHER_APP, 0)
        self.drag_dest_set(Gtk.DestDefaults.ALL, (torrent_target,), Gdk.DragAction.MOVE)

        view = TorrentListView(self.client.props.torrents, client=self.client, visible=True)
        self._filter_model = view.filter_model
        self._filter_model.set_visible_func(self._filter_model_func)
        self.main_sw.add(view)

        self._filter_model.connect('row-deleted', self._on_row_deleted)
        self._filter_model.connect('row-inserted', self._on_row_inserted)
        self.no_torrents.props.visible = len(self._filter_model) == 0

    def do_destroy(self):
        for hook in self._hooks:
            self.client.disconnect(hook)
        self._hooks = []
        Gtk.ApplicationWindow.do_destroy(self)

    def _init_actions(self):
        self._add_action = Gio.SimpleAction.new('torrent_add', GLib.VariantType('s'))
        self._add_action.connect('activate', self._on_torrent_add)
        self.add_action(self._add_action)

        self._add_uri_action = Gio.SimpleAction.new('torrent_add_uri', GLib.VariantType('s'))
        self._add_uri_action.connect('activate', self._on_torrent_add)
        self.add_action(self._add_uri_action)

        Action = namedtuple('Action', ('name', 'value', 'callback'))
        actions = (
            Action('filter_status', GLib.Variant('i', -1), self._on_status_filter),
            Action('filter_tracker', GLib.Variant('s', _('Any')), self._on_tracker_filter),
            Action('filter_directory', GLib.Variant('s', _('Any')), self._on_directory_filter),
        )

        for action in actions:
            act = Gio.SimpleAction.new_stateful(action.name, action.value.get_type(), action.value)
            act.connect('change-state', action.callback)
            self.add_action(act)

    def _on_connected_change(self, *args):
        if self.client.props.connected:
            self.main_stack.props.visible_child = self.main_box
            while self._queued_torrents:
                self._on_torrent_add_real(*self._queued_torrents.pop(0))
        else:
            self.main_stack.props.visible_child = self.warning_page

    def _on_speed_refresh(self, *args):
        subtitle = ''
        down = self.client.props.download_speed
        up = self.client.props.upload_speed
        if down:
            subtitle += '↓ {}/s'.format(GLib.format_size(down))
        if down and up:
            subtitle += ' — '
        if up:
            subtitle += '↑ {}/s'.format(GLib.format_size(up))
        self.header_bar.props.subtitle = subtitle

    def _on_row_deleted(self, model, path):
        if not self.no_torrents.props.visible and len(model) == 0:
            self.no_torrents.show()

    def _on_row_inserted(self, model, path, iter_):
        if self.no_torrents.props.visible and len(model):
            self.no_torrents.hide()

    @GtkTemplate.Callback
    def _on_alt_speed_toggled(self, button):
        self.client.session_set({'alt-speed-enabled': button.props.active})

    @GtkTemplate.Callback
    def _on_drag_data_received(self, widget, context, x, y, data, info, time):
        success = False

        for uri in data.get_data().split():
            with suppress(UnicodeDecodeError):
                uri = uri.decode('utf-8')
                if uri.endswith('.torrent'):
                    self._add_action.activate(GLib.Variant('s', uri))
                    success = True

        Gtk.drag_finish(context, success, success, time)

    @staticmethod
    @lru_cache(maxsize=1000)
    def _get_torrent_trackers(torrent) -> set:
        trackers = set()
        for tracker in ListStore(torrent.props.trackers):
            tracker_url = urlparse(tracker.props.announce).hostname
            trackers.add(tracker_url)
        return trackers

    @GtkTemplate.Callback
    def _on_filter_button_toggled(self, button):
        if not button.props.active:
            # Empty on close
            self.tracker_box.foreach(lambda child: child.destroy())
            self.directory_box.foreach(lambda child: child.destroy())
            return

        torrents = ListStore(self.client.props.torrents)

        trackers = set()
        for torrent in torrents:
            trackers |= self._get_torrent_trackers(torrent)
        for tracker in [_('Any')] + list(trackers):
            button = Gtk.ModelButton(text=tracker,
                                     action_name='win.filter_tracker',
                                     action_target=GLib.Variant('s', tracker),
                                     visible=True)
            self.tracker_box.add(button)

        # TODO: Might be a better way to show these
        directories = {torrent.props.download_dir.rstrip('/') for torrent in torrents}
        for directory in [_('Any')] + sorted(directories):
            label = directory.rpartition('/')[2]
            if len(label) >= 25:
                label = '…' + label[-24:]
            button = Gtk.ModelButton(text=label,
                                     action_name='win.filter_directory',
                                     action_target=GLib.Variant('s', directory),
                                     visible=True)
            self.directory_box.add(button)

    @GtkTemplate.Callback
    def _on_search_changed(self, entry):
        text = entry.get_text().lower() or None
        last_value = self._filter_text
        self._filter_text = text
        if last_value != text:
            self._filter_model.refilter()

    def _on_status_filter(self, action, value):
        new_value = value.get_int32()
        if new_value > TorrentStatus.SEED:
            return # Invalid

        action.set_state(value)
        if new_value < 0:
            self._filter = None
        else:
            self._filter = new_value
        self._filter_model.refilter()

    def _on_tracker_filter(self, action, value):
        new_value = value.get_string()

        action.set_state(value)
        if new_value == _('Any'):
            self._filter_tracker = None
        else:
            self._filter_tracker = new_value
        self._filter_model.refilter()

    def _on_directory_filter(self, action, value):
        new_value = value.get_string()

        action.set_state(value)
        if new_value == _('Any'):
            self._filter_directory = None
        else:
            self._filter_directory = new_value
        self._filter_model.refilter()

    @GtkTemplate.Callback
    def _on_search_toggle(self, button):
        active = button.props.active
        self.search_revealer.set_reveal_child(active)
        if not active:
            self.search_entry.props.text = ''
        else:
            self.search_entry.grab_focus()

    def _filter_model_func(self, model, it, data=None) -> bool:
        if self._filter is not None and model[it][TorrentColumn.status] != self._filter:
            return False
        if self._filter_text is not None and self._filter_text not in model[it][TorrentColumn.name].lower():
            return False
        if self._filter_directory is not None:
            if self._filter_directory != model[it][TorrentColumn.directory].rstrip('/'):
                return False
        if self._filter_tracker is not None:
            return self._filter_tracker in self._get_torrent_trackers(model[it][-1])
        return True

    def _on_torrent_add_real(self, uri, uri_only):
        for dialog in self._add_dialogs:
            if dialog.uri == uri:
                dialog.present()
                logging.info('Raising existing dialog for {}'.format(uri))
                return

        if uri_only is True:
            dialog = AddURIDialog(transient_for=self,
                                  uri=uri,
                                  client=self.client)
        else:
            dialog = AddDialog(transient_for=self,
                               uri=uri,
                               client=self.client)
        self._add_dialogs.append(dialog)
        dialog.connect('destroy', lambda d: self._add_dialogs.remove(d))
        dialog.present()

    def _on_torrent_add(self, action, param):
        file = param.get_string()
        uri_only = action is self._add_uri_action
        if self.client.props.connected:
            self._on_torrent_add_real(file, uri_only)
        else:
            self._queued_torrents.append((file, uri_only))
