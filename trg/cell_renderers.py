# cell_renderers.py
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
from gi.repository import (
	GLib,
	GObject,
	Gio,
	Gtk,
)
from .torrent import TorrentStatus


class CellRendererSize(Gtk.CellRendererText):
	__gtype_name__ = 'TrgCellRendererSize'

	size = GObject.Property(type=GObject.TYPE_UINT64)

	def __init__(self, **kwargs):
		super().__init__(text='', **kwargs)
		self.connect('notify::size', self._on_size_change)

	def _on_size_change(self, prop, param):
		self.set_property('text', GLib.format_size(self.size))


class CellRendererSpeed(Gtk.CellRendererText):
	__gtype_name__ = 'TrgCellRendererSpeed'

	speed = GObject.Property(type=GObject.TYPE_UINT64)

	def __init__(self, **kwargs):
		super().__init__(text='', **kwargs)
		self.connect('notify::speed', self._on_speed_change)

	def _on_speed_change(self, prop, param):
		if self.speed:
			self.props.text = GLib.format_size(self.speed) + '/s'
		else:
			self.props.text = ''


class CellRendererPercent(Gtk.CellRendererProgress):
	__gtype_name__ = 'TrgCellRendererPercent'

	percent = GObject.Property(type=float)

	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.connect('notify::percent', self._on_percent_change)

	def _on_percent_change(self, prop, param):
		self.props.value = int(self.percent * 100)


STATUS_ICONS = {
	TorrentStatus.STOPPED: Gio.ThemedIcon.new('media-playback-pause-symbolic'),
	TorrentStatus.DOWNLOAD: Gio.ThemedIcon.new('network-transmit-receive-symbolic'),
	TorrentStatus.SEED: Gio.ThemedIcon.new('network-transmit-symbolic'),
	TorrentStatus.CHECK: Gio.ThemedIcon.new('emblem-synchronizing-symbolic'),

	TorrentStatus.CHECK_WAIT: Gio.ThemedIcon.new('content-loading-symbolic'),
	TorrentStatus.DOWNLOAD_WAIT: Gio.ThemedIcon.new('content-loading-symbolic'),
	TorrentStatus.SEED_WAIT: Gio.ThemedIcon.new('content-loading-symbolic'),
}


class CellRendererStatus(Gtk.CellRendererPixbuf):
	__gtype_name__ = 'TrgCellRendererStatus'

	status = GObject.Property(type=GObject.TYPE_UINT64)

	def __init__(self, **kwargs):
		super().__init__(gicon=None, **kwargs)
		self.connect('notify::status', self._on_status_change)

	def _on_status_change(self, prop, param):
		icon = STATUS_ICONS.get(self.props.status)
		self.props.gicon = icon
		if not icon:
			logging.warning('Icon for status {} not found!'.format(self.props.status))
