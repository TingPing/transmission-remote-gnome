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
from collections import OrderedDict

from gi.repository import (
	GLib,
	GObject,
	Pango,
	Gtk,
)

from .torrent import Torrent
from .list_wrapper import WrappedStore
from .torrent_file_view import CellRendererSize
from .gi_composites import GtkTemplate

@GtkTemplate(ui='/io/github/Trg/ui/torrentview.ui')
class TorrentListView(Gtk.TreeView):
	__gtype_name__ = 'TorrentListView'

	size_column = GtkTemplate.Child()
	progress_column = GtkTemplate.Child()
	down_column = GtkTemplate.Child()
	up_column = GtkTemplate.Child()

	def __init__(self, model, **kwargs):
		super().__init__(**kwargs)
		self.init_template()
		self._init_cells()

		# NOTE: Order must match TorrentColumn enum
		props = OrderedDict()
		props['name'] = str
		props['size-when-done'] = GObject.TYPE_UINT64
		props['percent-done'] = float
		props['rate-download'] = GObject.TYPE_UINT64
		props['rate-upload'] = GObject.TYPE_UINT64
		props['status'] = GObject.TYPE_UINT64
		s = WrappedStore.new_for_model(model, props)
		self.filter_model = Gtk.TreeModelFilter(child_model=s)
		self._sort_model = Gtk.TreeModelSort(model=self.filter_model)
		self.props.model = self._sort_model

		# Workaround random crash?
		s.insert_with_valuesv(0, [0], ['FIXME'])
		GLib.timeout_add(0.1, lambda: s.clear())

	def _init_cells(self):
		area = self.size_column.props.cell_area
		area.clear()
		renderer = CellRendererSize(alignment=Pango.Alignment.RIGHT)
		area.add(renderer)
		area.add_attribute(renderer, 'size', TorrentColumn.size)

		area = self.progress_column.props.cell_area
		area.clear()
		renderer = CellRendererPercent()
		area.add(renderer)
		area.add_attribute(renderer, 'percent', TorrentColumn.progress)

		area = self.down_column.props.cell_area
		area.clear()
		renderer = CellRendererSpeed()
		area.add(renderer)
		area.add_attribute(renderer, 'speed', TorrentColumn.down)

		area = self.up_column.props.cell_area
		area.clear()
		renderer = CellRendererSpeed()
		area.add(renderer)
		area.add_attribute(renderer, 'speed', TorrentColumn.up)


class TorrentColumn(IntEnum):
	name = 0
	size = 1
	progress = 2
	down = 3
	up = 4
	status = 5


class CellRendererSpeed(Gtk.CellRendererText):
	__gtype_name__ = 'CellRendererSpeed'

	speed = GObject.Property(type=GObject.TYPE_UINT64)

	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.connect('notify::speed', self._on_speed_change)

	def _on_speed_change(self, prop, param):
		if self.speed:
			self.props.text = GLib.format_size(self.speed) + '/s'
		else:
			self.props.text = ''


class CellRendererPercent(Gtk.CellRendererProgress):
	__gtype_name__ = 'CellRendererPercent'

	percent = GObject.Property(type=float)

	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.connect('notify::percent', self._on_percent_change)

	def _on_percent_change(self, prop, param):
		self.props.value = int(self.percent * 100)
		
