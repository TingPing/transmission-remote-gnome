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
from .torrent_list_view import TorrentListView
from .add_dialog import AddDialog
from .client import Client

@GtkTemplate(ui='/io/github/Trg/ui/applicationwindow.ui')
class ApplicationWindow(Gtk.ApplicationWindow):
	__gtype_name__ = 'ApplicationWindow'

	client = GObject.Property(type=Client)
	torrent_sw = GtkTemplate.Child()

	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.init_template()
		self._init_actions()

		settings = Gio.Settings.new('io.github.Trg')

		self.client = Client(username=settings['username'], password=settings['password'])
		self.client.refresh_all()
		view = TorrentListView(model=self.client.props.torrents)
		self.torrent_sw.add(view)
		view.show_all()

	def _init_actions(self):
		action = Gio.SimpleAction.new('torrent_add', GLib.VariantType('s'))
		action.connect('activate', self._on_torrent_add)
		self.add_action(action)

	def _on_torrent_add(self, action, param):
		dialog = AddDialog(transient_for=self, modal=True,
		                   uri=param.get_string(),
		                   client=self.client)
		dialog.present()

