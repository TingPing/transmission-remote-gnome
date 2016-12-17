# application.py
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
from gettext import gettext as _

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import (
    GLib,
	GObject,
    Gio,
    Gtk
)

from .client import Client
from .window import ApplicationWindow

class Application(Gtk.Application):
	__gtype_name__ = 'Application'

	version = GObject.Property(type=str, flags=GObject.ParamFlags.CONSTRUCT_ONLY|GObject.ParamFlags.READWRITE)

	def __init__(self, **kwargs):
		super().__init__(application_id='se.tingping.Trg',
		                 flags=Gio.ApplicationFlags.HANDLES_OPEN, **kwargs)

		if GLib.get_prgname() == '__main__.py':
			GLib.set_prgname('transmission-remote-gnome')

		self.window = None

		self.add_main_option('log', 0, GLib.OptionFlags.NONE, GLib.OptionArg.INT,
		                     _('Set log level'), None)

	def do_startup(self):
		Gtk.Application.do_startup(self)

		action = Gio.SimpleAction.new('quit', None)
		action.connect('activate', lambda action, param: self.quit())
		self.add_action(action)

		action = Gio.SimpleAction.new('about', None)
		action.connect('activate', self.on_about)
		self.add_action(action)

	def do_open(self, files, n_files, hint):
		self.activate()
		for f in files:
			self.window.activate_action('torrent_add', GLib.Variant('s', f.get_uri()))

	def do_handle_local_options(self, options):
		if options.contains('log'):
			level = options.lookup_value('log', GLib.VariantType('i')).get_int32()
			if level >= 3:
				level = logging.DEBUG
			elif level == 2:
				level = logging.INFO
			elif level == 1:
				level = logging.WARN
			else:
				level = logging.ERROR

			# TODO: Improve logging format
			logging.basicConfig(level=level,
                       format=' %(levelname)s | %(module)s.%(funcName)s:%(lineno)d\t| %(message)s')
			options.remove('log')

		return Gtk.Application.do_handle_local_options(self, options)

	def do_activate(self):
		if not self.window:
			self.window = ApplicationWindow(application=self)

		self.window.present()

	def do_shutdown(self):
		Gtk.Application.do_shutdown(self)

	def on_about(self, action, param):
		about = Gtk.AboutDialog(transient_for=self.window, modal=True,
		                        license_type=Gtk.License.GPL_3_0,
		                        authors=['Patrick Griffis', ],
		                        copyright='Copyright © 2016 Patrick Griffis',
		                        logo_icon_name='transmission',
		                        version=self.version)
		about.present()
