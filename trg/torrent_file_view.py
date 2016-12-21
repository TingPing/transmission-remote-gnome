# torrent_file_view.py
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
from gettext import gettext as _

from gi.repository import (
	GLib,
	GObject,
	Gdk,
	Gtk,
)

from .gi_composites import GtkTemplate

DEFAULT_PRI_STR = _('Normal')
DEFAULT_PRI_VAL = 0


@GtkTemplate(ui='/se/tingping/Trg/ui/fileview.ui')
class TorrentFileView(Gtk.TreeView):
	__gtype_name__ = 'TorrentFileView'

	torrent_file_store = GtkTemplate.Child()

	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.init_template()

	def _set_selection_value(self, item, user_data=None):
		selection = self.get_selection()
		model, iters = selection.get_selected_rows()
		column, val = user_data

		for it in iters:
			if column == FileColumn.download:
				self._set_download_value(model, it, val)
			elif column == FileColumn.pri_val:
				self._set_priority_value(model, it, *val)

	def _build_menu(self):
		MENU_ITEMS = (
			(_('Download'), FileColumn.download, True),
			(_('Skip'), FileColumn.download, False),
			(),
			(_('Priority High'), FileColumn.pri_val, (1, _('High'))),
			(_('Priority Normal'), FileColumn.pri_val, (0, _('Normal'))),
			(_('Priority Low'), FileColumn.pri_val, (-1, _('Low'))),
		)

		menu = Gtk.Menu.new()
		for entry in MENU_ITEMS:
			if entry:
				item = Gtk.MenuItem.new_with_label(entry[0])
				item.connect('activate', self._set_selection_value, entry[1:])
			else:
				item = Gtk.SeparatorMenuItem.new()
			menu.append(item)

		menu.attach_to_widget(self)
		menu.show_all()
		return menu

	def do_button_press_event(self, event):
		if not (event.type == Gdk.EventType.BUTTON_PRESS and event.button == Gdk.BUTTON_SECONDARY):
			return Gtk.TreeView.do_button_press_event(self, event)

		ret = self.get_path_at_pos(event.x, event.y)
		if not ret or not ret[0]:
			return Gdk.EVENT_STOP

		path = ret[0]
		selection = self.get_selection()
		if not selection.path_is_selected(path):
			selection.unselect_all()
			selection.select_path(path)

		menu = self._build_menu()
		if hasattr(menu, 'popup_at_pointer'):
			menu.popup_at_pointer(event) # Gtk 3.22
		else:
			menu.popup(None, None, None, None, event.button, event.time)
		return Gdk.EVENT_STOP

	# TODO: Avoid recursion because python
	def _add_node_to_store(self, parent, node):
		parent = self.torrent_file_store.append(parent, [node.name, node.get_size(), True,
		                                                 DEFAULT_PRI_VAL, DEFAULT_PRI_STR, node.index,
		                                                 False])
		for child in node.children:
			self._add_node_to_store(parent, child)

	def set_torrent_file(self, torrent):
		self.torrent_file_store.clear()
		self._add_node_to_store(None, torrent.files)
		self.expand_all()

	@staticmethod
	def _iter_get_children(rowiter):
		yield from rowiter.iterchildren()
		for child in rowiter.iterchildren():
			yield from TorrentFileView._iter_get_children(child)

	def _set_priority_value(self, model, it, pri_val, pri_str):
		model[it][FileColumn.pri_val] = pri_val
		model[it][FileColumn.pri_str] = pri_str

		# Set any children to new state
		for child in self._iter_get_children(model[it]):
			child[FileColumn.pri_val] = pri_val
			child[FileColumn.pri_str] = pri_str

		# Set any parent to inconsistent
		parent = model[it].get_parent()
		while parent:
			for child in parent.iterchildren():
				if child[FileColumn.pri_val] != pri_val:
					parent[FileColumn.pri_str] = _('Mixed')
					break
			else:
				parent[FileColumn.pri_str] = pri_str
			parent = parent.get_parent()

	@GtkTemplate.Callback
	def _on_file_priority_changed(self, cell, path, new_iter):
		pri_model = cell.props.model
		pri_val = pri_model[new_iter][PriorityColumn.pri_val]
		pri_str = _(pri_model[new_iter][PriorityColumn.pri_str])

		model = self.torrent_file_store
		it = model.get_iter(path)
		self._set_priority_value(model, it, pri_val, pri_str)

	def _set_download_value(self, model, it, val):
		model[it][FileColumn.download] = val

		for child in self._iter_get_children(model[it]):
			child[FileColumn.download] = val
		model[it][FileColumn.download_inconsistent] = False

		parent = model[it].get_parent()
		while parent:
			for child in parent.iterchildren():
				if child[FileColumn.download] != val:
					parent[FileColumn.download] = False
					parent[FileColumn.download_inconsistent] = True
					break
			else:
				parent[FileColumn.download] = val
				parent[FileColumn.download_inconsistent] = False
			parent = parent.get_parent()

	@GtkTemplate.Callback
	def _on_file_download_toggled(self, cell, path):
		model = self.torrent_file_store
		it = model.get_iter(path)
		val = not model[it][FileColumn.download] # Toggled
		self._set_download_value(model, it, val)


class FileColumn(IntEnum):
	name = 0
	size = 1
	download = 2
	pri_val = 3
	pri_str = 4
	index = 5
	download_inconsistent = 6


class PriorityColumn(IntEnum):
	pri_val = 0
	pri_str = 1


class CellRendererSize(Gtk.CellRendererText):
	__gtype_name__ = 'TrgCellRendererSize'

	size = GObject.Property(type=GObject.TYPE_UINT64)

	def __init__(self, **kwargs):
		super().__init__(text='', **kwargs)
		self.connect('notify::size', self._on_size_change)

	def _on_size_change(self, prop, param):
		self.set_property('text', GLib.format_size(self.size))
