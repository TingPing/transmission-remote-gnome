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
from .torrent_file_view import *

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

	def __init__(self, **kwargs):
		super().__init__(use_header_bar=1, **kwargs)
		self.init_template()

		self.set_response_sensitive(Gtk.ResponseType.OK, False)
		self.settings = Gio.Settings.new('se.tingping.Trg')
		self.settings.bind('add-paused', self.paused_check, 'active', Gio.SettingsBindFlags.DEFAULT)
		self.settings.bind('delete-on-add', self.delete_check, 'active', Gio.SettingsBindFlags.DEFAULT)

		self.fileview = TorrentFileView()
		self.fileview_sw.add(self.fileview)

		self.cancellable = Gio.Cancellable.new()

		self.destination_combo.append_text('/mnt/Media') # TODO: Remote setting
		self.destination_combo.set_active(0)

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

		for row in self.fileview.props.model:
			index = row[FileColumn.index]
			if index == -1: # Directory
				continue

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
				_file.trash_async(GLib.PRIORITY_DEFAULT, None, None)

		if response_id != Gtk.ResponseType.DELETE_EVENT:
			self.destroy()

	def _on_uri_change(self, *args):
		self.file_chooser.set_uri(self.uri)
		self.torrent = TorrentFile.new_for_uri(self.uri, self.cancellable)
		self.torrent.connect('file-loaded', self._on_file_loaded)
		self.torrent.connect('file-invalid', self._on_file_invalid)

	def _on_file_invalid(self, torrent, error):
		dialog = Gtk.MessageDialog(text='Failed to read torrent file: {}'.format(error),
                           message_type=Gtk.MessageType.ERROR,
                           transient_for=self, modal=True)
		dialog.present()
		self.torrent = None
		self.set_response_sensitive(Gtk.ResponseType.OK, False)

	def _on_file_loaded(self, torrent):
		self.fileview.set_torrent_file(torrent)
		self.set_response_sensitive(Gtk.ResponseType.OK, True)

	@GtkTemplate.Callback
	def _on_destination_changed(self, combobox):
		path = combobox.get_active_text()
		self.set_response_sensitive(Gtk.ResponseType.OK,
		                            bool(GLib.path_is_absolute(path) and self.torrent))

	@GtkTemplate.Callback
	def _on_file_set(self, chooser):
		self.uri = chooser.get_uri()


