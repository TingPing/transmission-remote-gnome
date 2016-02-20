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

import gi
gi.require_version('Pango', '1.0')
from gi.repository import (
	GLib,
    GObject,
    Gio,
    Pango,
    Gtk,
)

from .torrent import Torrent

class TorrentListView(Gtk.ListBox):
	__gtype_name__ = 'TorrentListView'

	model = GObject.Property(type=Gio.ListModel)

	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.bind_model(self.model, self._on_create_row)

	@staticmethod
	def _on_create_row(item):
		return TorrentBox(torrent=item)

class TorrentBox(Gtk.Box):
	__gtype_name__ = 'TorrentBox'

	torrent = GObject.Property(type=Torrent, flags=GObject.ParamFlags.CONSTRUCT_ONLY|GObject.ParamFlags.READWRITE)

	def __init__(self, **kwargs):
		super().__init__(orientation=Gtk.Orientation.VERTICAL, **kwargs)

		self.name_lbl = Gtk.Label(halign=Gtk.Align.START,
		                          ellipsize=Pango.EllipsizeMode.END,
		                          lines=1)
		self.pack_start(self.name_lbl, False, True, 5)

		self.set_name(self.torrent.props.name)
		self.torrent.connect('notify::name', lambda obj, param: self.set_name(obj.props.name))

		bar = Gtk.ProgressBar(show_text=True)
		bar.props.text = '{}/{}'.format(GLib.format_size(self.torrent.size_when_done * self.torrent.percent_done),
										GLib.format_size(self.torrent.size_when_done))
		self.torrent.bind_property('percent_done', bar, 'fraction', GObject.BindingFlags.SYNC_CREATE)
		self.pack_start(bar, False, True, 5)

		self.show_all()

	def set_name(self, text:str):
		esc = GLib.markup_escape_text(text)
		self.name_lbl.set_markup('<b>{}</b>'.format(esc))

	def set_size_line(self, text:str):
		pass
