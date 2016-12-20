# preferences_dialog.py
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
from os import path
from gettext import gettext as _
from collections import namedtuple
from gi.repository import (
	GLib,
	Gio,
	Gtk,
)

from .gi_composites import GtkTemplate


@GtkTemplate(ui='/se/tingping/Trg/ui/preferencesdialog.ui')
class PreferencesDialog(Gtk.Dialog):
	__gtype_name__ = 'PreferencesDialog'

	local_stack = GtkTemplate.Child()
	remote_stack = GtkTemplate.Child()

	def __init__(self, **kwargs):
		super().__init__(use_header_bar=1, **kwargs)
		self.init_template()
		self.settings = Gio.Settings.new('se.tingping.Trg')

		Row = namedtuple('Row', ['title', 'widget', 'bind_property', 'setting'])

		self._autostart_switch = AutoStartSwitch()

		settings_map = {
			('connection', _('Connection')): [
				Row(_('Hostname:'), Gtk.Entry.new(), 'text', 'hostname'),
				Row(_('Port:'), Gtk.SpinButton.new_with_range(0, GLib.MAXUINT16, 1), 'value', 'port'),
				Row(_('Username:'), Gtk.Entry.new(), 'text', 'username'),
				Row(_('Password:'), Gtk.Entry(visibility=False, input_purpose=Gtk.InputPurpose.PASSWORD), 'text',
					'password'),
			],
			('service', _('Service')): [
				Row(_('Automatically load downloaded torrent files:'), Gtk.Switch.new(), 'active',
					'watch-downloads-directory'),
				Row(_('Show notifications when downlods complete:'), Gtk.Switch.new(), 'active',
				 	'notify-on-finish'),
				Row(_('Autostart service on login:'), self._autostart_switch, '', ''),
			]
		}

		for page, rows in settings_map.items():
			box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 4)
			for row in rows:
				row_box = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 4)
				row_box.add(Gtk.Label.new(row.title))
				row_box.add(row.widget)

				if row.bind_property and row.setting:
					self.settings.bind(row.setting, row.widget, row.bind_property,
									   Gio.SettingsBindFlags.DEFAULT|Gio.SettingsBindFlags.NO_SENSITIVITY)
				box.add(row_box)
			box.show_all()
			self.local_stack.add_titled(box, page[0], page[1])

	def do_show(self):
		Gtk.Dialog.do_show(self)
		self.settings.delay()

	def do_response(self, response_id):
		if response_id == Gtk.ResponseType.APPLY:
			self.settings.apply()
			self._autostart_switch.apply()
		else:
			self.settings.revert()

		if response_id != Gtk.ResponseType.DELETE_EVENT:
			self.destroy()


class AutoStartSwitch(Gtk.Switch):
	def __init__(self, **kwargs):
		super().__init__(sensitive=False, **kwargs)

		autostart_file_path = path.join(GLib.get_user_config_dir(), 'autostart',
										'se.tingping.Trg.service.desktop')

		self.autostart_file = Gio.File.new_for_path(autostart_file_path)
		logging.debug('Querying {} to see if it exists'.format(self.autostart_file))
		self.autostart_file.query_info_async(Gio.FILE_ATTRIBUTE_STANDARD_TYPE, Gio.FileQueryInfoFlags.NONE,
										GLib.PRIORITY_DEFAULT, callback=self._on_file_query)

	def _on_file_query(self, autostart_file, result):
		try:
			autostart_file.query_info_finish(result)
			self.props.active = True
			logging.debug('Autostart file exists')
		except GLib.Error as e:
			self.props.active = False
			logging.debug('Querying autostart file returned: {}'.format(e))
		self.props.sensitive = True

	def apply(self):
		"""Creates or deletes the autostart file based upon current state"""
		if not self.props.sensitive: # We never got the current state
			return

		if self.props.active:
			logging.info('Creating autostart file')
			source = Gio.File.new_for_uri('resource:///se/tingping/Trg/se.tingping.Trg.service.desktop')
			if hasattr(source, 'copy_async'):
				# TODO: Fix upstream in GLib
				source.copy_async(self.autostart_file, Gio.FileCopyFlags.NONE, GLib.PRIORITY_DEFAULT)
			else:
				try:
					source.copy(self.autostart_file, Gio.FileCopyFlags.NONE)
				except GLib.Error:
					pass
		else:
			logging.info('Deleting autostart file')
			self.autostart_file.delete_async(GLib.PRIORITY_DEFAULT)
