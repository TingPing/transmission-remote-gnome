# add_dialog.py
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


from gi.repository import (
    GLib,
    GObject,
    Gio,
    Gtk,
)

from .gi_composites import GtkTemplate
from .client import Client
from .torrent_file import TorrentFile
from .torrent_file_view import TorrentFileView, FileColumn
from .list_model_override import ListStore


@GtkTemplate(ui='/se/tingping/Trg/ui/adddialog.ui')
class AddDialog(Gtk.Dialog):
    __gtype_name__ = 'AddDialog'

    uri = GObject.Property(type=str)
    client = GObject.Property(type=Client)
    torrent = GObject.Property(type=TorrentFile)

    file_chooser = GtkTemplate.Child()
    destination_combo = GtkTemplate.Child()
    fileview_sw = GtkTemplate.Child()
    paused_check = GtkTemplate.Child()
    delete_check = GtkTemplate.Child()
    priority_combo = GtkTemplate.Child()
    fileview = GtkTemplate.Child()

    def __init__(self, **kwargs):
        super().__init__(use_header_bar=1, **kwargs)
        self.init_template()

        self.set_response_sensitive(Gtk.ResponseType.OK, False)
        self.settings = Gio.Settings.new('se.tingping.Trg')
        self.settings.bind('add-paused', self.paused_check, 'active', Gio.SettingsBindFlags.DEFAULT)
        self.settings.bind('delete-on-add', self.delete_check, 'active', Gio.SettingsBindFlags.DEFAULT)

        self.cancellable = Gio.Cancellable.new()

        self.destination_combo.append_text(self.client.props.download_dir)
        self.destination_combo.set_active(0)
        torrent_directories = {torrent.props.download_dir.rstrip('/')
                               for torrent in ListStore(self.client.props.torrents)}
        for directory in sorted(torrent_directories):
            self.destination_combo.append_text(directory)

        self.connect('notify::uri', self._on_uri_change)
        if self.uri:
            self._on_uri_change()

    def __del__(self):
        self.cancellable.cancel()

    def _make_args(self):
        if not self.torrent:
            return {}

        files_wanted = []
        files_unwanted = []
        pri_high = []
        pri_norm = []
        pri_low = []

        store = self.fileview.props.model

        # FIXME: Recursion and Ugly
        def iterate_model(_iter):
            while _iter is not None:
                if store.iter_has_child(_iter):
                    iterate_model(store.iter_children(_iter))
                else:
                    row = store[_iter]
                    index = row[FileColumn.index]

                    if row[FileColumn.download]:
                        files_wanted.append(index)
                    else:
                        files_unwanted.append(index)

                    if row[FileColumn.pri_val] == -1:
                        pri_low.append(index)
                    elif row[FileColumn.pri_val] == 0:
                        pri_norm.append(index)
                    elif row[FileColumn.pri_val] == 1:
                        pri_high.append(index)

                _iter = store.iter_next(_iter)

        iterate_model(store.get_iter_first())

        args = {
            'metainfo': self.torrent.get_base64(),
            'download-dir': self.destination_combo.get_active_text(),
            'priority-low': pri_low,
            'priority-normal': pri_norm,
            'priority-high': pri_high,
            'files-wanted': files_wanted,
            'files-unwanted': files_unwanted,
            'paused': self.paused_check.get_active(),
            'bandwidthPriority': int(self.priority_combo.get_active_id()),
        }

        return args

    def do_response(self, response_id):
        if response_id == Gtk.ResponseType.OK:
            args = self._make_args()
            self.client.torrent_add(args)
            if self.settings['delete-on-add']:
                _file = Gio.File.new_for_uri(self.uri)
                _file.trash_async(GLib.PRIORITY_DEFAULT)

        if response_id != Gtk.ResponseType.DELETE_EVENT:
            self.destroy()

    def _on_uri_change(self, *args):
        self.file_chooser.set_uri(self.uri)
        self.torrent = TorrentFile.new_for_uri(self.uri, self.cancellable)
        self.torrent.connect('file-loaded', self._on_file_loaded)
        self.torrent.connect('file-invalid', self._on_file_invalid)

    def _on_file_invalid(self, torrent, error):
        def on_response(dialog, response):
            if response != Gtk.ResponseType.DELETE_EVENT:
                dialog.destroy()

        dialog = Gtk.MessageDialog(text='Failed to read torrent file: {}'.format(error),
                                   message_type=Gtk.MessageType.ERROR,
                                   buttons=Gtk.ButtonsType.CLOSE,
                                   transient_for=self, modal=True)
        dialog.connect('response', on_response)
        dialog.present()
        self.torrent = None
        self.set_response_sensitive(Gtk.ResponseType.OK, False)

    def _on_file_loaded(self, torrent):
        self.fileview.set_torrent_file(torrent)
        self.set_response_sensitive(Gtk.ResponseType.OK,
                                    GLib.path_is_absolute(self.destination_combo.get_active_text()))

    @GtkTemplate.Callback
    def _on_destination_changed(self, combobox):
        path = combobox.get_active_text()
        self.set_response_sensitive(Gtk.ResponseType.OK,
                                    bool(GLib.path_is_absolute(path) and self.torrent))

    @GtkTemplate.Callback
    def _on_file_set(self, chooser):
        self.uri = chooser.get_uri()


@GtkTemplate(ui='/se/tingping/Trg/ui/adduridialog.ui')
class AddURIDialog(Gtk.Dialog):
    __gtype_name__ = 'AddURIDialog'

    uri = GObject.Property(type=str)
    client = GObject.Property(type=Client)
    uri_entry = GtkTemplate.Child()
    paused_check = GtkTemplate.Child()

    def __init__(self, **kwargs):
        super().__init__(use_header_bar=1, **kwargs)
        self.init_template()

        self.settings = Gio.Settings.new('se.tingping.Trg')
        self.settings.bind('add-paused', self.paused_check, 'active', Gio.SettingsBindFlags.DEFAULT)

        self.uri_entry.connect('notify::text', self._on_entry_text_changed)
        self.uri_entry.props.text = self.uri
        self._on_entry_text_changed()
        self.uri_entry.grab_focus()

    def _on_entry_text_changed(self, entry=None, pspec=None):
        self.set_response_sensitive(Gtk.ResponseType.OK, self.uri_entry.props.text != '')

    def do_response(self, response_id):
        if response_id == Gtk.ResponseType.OK:
            args = {
                'filename': self.uri_entry.props.text,
                'paused': self.paused_check.props.active,
            }
            self.client.torrent_add(args)

        if response_id != Gtk.ResponseType.DELETE_EVENT:
            self.destroy()
