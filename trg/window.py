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
from .add_dialog import AddDialog
from .client import Client
from .torrent import TorrentStatus


@GtkTemplate(ui='/se/tingping/Trg/ui/applicationwindow.ui')
class ApplicationWindow(Gtk.ApplicationWindow):
	__gtype_name__ = 'ApplicationWindow'

	client = GObject.Property(type=Client)
	torrent_sw = GtkTemplate.Child()
	search_entry = GtkTemplate.Child()
	search_revealer = GtkTemplate.Child()
	header_bar = GtkTemplate.Child()
	alt_speed_toggle = GtkTemplate.Child()

	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.init_template()
		self._init_actions()
		self._filter = None
		self._filter_text = None
		self._filter_tracker = None

		self.client.connect('notify::download-speed', self._on_speed_refresh)
		self.client.bind_property('alt-speed-enabled', self.alt_speed_toggle,
		                          'active', GObject.BindingFlags.SYNC_CREATE)

		torrent_target = Gtk.TargetEntry.new('text/uri-list', Gtk.TargetFlags.OTHER_APP, 0)
		self.drag_dest_set(Gtk.DestDefaults.ALL, (torrent_target,), Gdk.DragAction.MOVE)

		view = TorrentListView(self.client.props.torrents, client=self.client)
		self._filter_model = view.filter_model
		self._filter_model.set_visible_func(self._filter_model_func)
		self.torrent_sw.add(view)
		view.show_all()

	def _init_actions(self):
		self._add_action = Gio.SimpleAction.new('torrent_add', GLib.VariantType('s'))
		self._add_action.connect('activate', self._on_torrent_add)
		self.add_action(self._add_action)

		default_value = GLib.Variant('i', -1) # All
		action = Gio.SimpleAction.new_stateful('filter_status', default_value.get_type(), default_value)
		action.connect('change-state', self._on_status_filter)
		self.add_action(action)

		default_value = GLib.Variant('s', 'All')
		action = Gio.SimpleAction.new_stateful('filter_tracker', default_value.get_type(), default_value)
		action.connect('change-state', self._on_tracker_filter)
		self.add_action(action)

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
	def _on_filter_button_toggled(self, button, filter_box):
		if not button.props.active:
			# Empty on close
			filter_box.foreach(lambda child: child.destroy())
			return

		trackers = set()
		for torrent in ListStore(self.client.props.torrents):
			trackers |= self._get_torrent_trackers(torrent)

		for tracker in ['All'] + list(trackers):
			button = Gtk.ModelButton(text=tracker,
									 action_name='win.filter_tracker',
									 action_target=GLib.Variant('s', tracker))
			filter_box.add(button)
		filter_box.show_all()

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
		if new_value == 'All':
			self._filter_tracker = None
		else:
			self._filter_tracker = new_value
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
		if self._filter_tracker is not None:
			return self._filter_tracker in self._get_torrent_trackers(model[it][-1])
		return True

	def _on_torrent_add(self, action, param):
		dialog = AddDialog(transient_for=self,
		                   uri=param.get_string(),
		                   client=self.client)
		dialog.present()
