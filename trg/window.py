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

from gettext import gettext as _

from gi.repository import (
	GLib,
    GObject,
    Gio,
    Gtk,
)

from .gi_composites import GtkTemplate
from .torrent_list_view import TorrentListView, TorrentColumn
from .add_dialog import AddDialog
from .client import Client
from .torrent import TorrentStatus

@GtkTemplate(ui='/se/tingping/Trg/ui/applicationwindow.ui')
class ApplicationWindow(Gtk.ApplicationWindow):
	__gtype_name__ = 'ApplicationWindow'

	client = GObject.Property(type=Client)
	torrent_sw = GtkTemplate.Child()

	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.init_template()
		self._init_actions()
		self._filter = None

		settings = Gio.Settings.new('se.tingping.Trg')

		self.client = Client(username=settings['username'], password=settings['password'])
		self.client.refresh_all()

		view = TorrentListView(self.client.props.torrents)
		self._filter_model = view.filter_model
		self._filter_model.set_visible_func(self._filter_model_func)
		self.torrent_sw.add(view)
		view.show_all()

	def _init_actions(self):
		action = Gio.SimpleAction.new('torrent_add', GLib.VariantType('s'))
		action.connect('activate', self._on_torrent_add)
		self.add_action(action)

		default_value = GLib.Variant('i', -1) # All
		action = Gio.SimpleAction.new_stateful('filter_status', default_value.get_type(),
                                                                default_value)
		action.connect('change-state', self._on_status_filter)
		self.add_action(action)

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

	def _filter_model_func(self, model, it, data=None):
		if self._filter is None:
			return True
		return model[it][TorrentColumn.status] == self._filter

	def _on_torrent_add(self, action, param):
		dialog = AddDialog(transient_for=self, modal=True,
		                   uri=param.get_string(),
		                   client=self.client)
		dialog.present()

