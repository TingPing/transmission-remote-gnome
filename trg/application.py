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

import gi
from gi.repository import (
    GLib,
    GObject,
    Gio,
    Gdk,
    Gtk
)

from .window import ApplicationWindow
from .preferences_dialog import PreferencesDialog
from .client import Client

try:
    gi.require_version('StatusNotifier', '1.0')
    from gi.repository import StatusNotifier
except (ImportError, ValueError):
    StatusNotifier = None


class Application(Gtk.Application):
    __gtype_name__ = 'Application'

    version = GObject.Property(type=str, flags=GObject.ParamFlags.CONSTRUCT_ONLY|GObject.ParamFlags.READWRITE)

    def __init__(self, **kwargs):
        super().__init__(application_id='se.tingping.Trg',
                         flags=Gio.ApplicationFlags.HANDLES_OPEN, **kwargs)

        if GLib.get_prgname() == '__main__.py':
            GLib.set_prgname('transmission-remote-gnome')

        self.window = None
        self.client = None
        self.download_monitor = None
        self.status = None
        self.settings = Gio.Settings.new('se.tingping.Trg')

        self.add_main_option('log', 0, GLib.OptionFlags.NONE, GLib.OptionArg.INT,
                             _('Set log level'), None)

    def do_startup(self):
        Gtk.Application.do_startup(self)

        action = Gio.SimpleAction.new('quit')
        action.connect('activate', lambda act, param: self.quit())
        self.add_action(action)
        self.set_accels_for_action('app.quit', ['<Primary>q'])

        action = Gio.SimpleAction.new('about')
        action.connect('activate', self.on_about)
        self.add_action(action)

        action = Gio.SimpleAction.new('preferences')
        action.connect('activate', self.on_preferences)
        self.add_action(action)

        action = Gio.SimpleAction.new('open-uri', GLib.VariantType('s'))
        action.connect('activate', self._on_open_uri)
        self.add_action(action)

        self._init_service()
        self.settings.connect('changed::show-status-icon', self._on_status_icon_change)
        self._on_status_icon_change()

    def _on_status_icon_change(self, settings=None, key=None):
        if StatusNotifier is None:
            return

        enabled = self.settings['show-status-icon']

        if enabled is True and self.status is None:  # Ran once
            self.status = StatusNotifier.Item.new_from_icon_name(self.props.application_id,
                                                                 StatusNotifier.Category.APPLICATION_STATUS,
                                                                 'se.tingping.Trg-symbolic')
            self.status.connect('activate', lambda sn, x, y: self.activate())
            self.status.holding = False

            def on_registration_failed(sn, pspec):
                if sn.holding is True:
                    self.release()
                    sn.holding = False

            self.status.connect('registration-failed', on_registration_failed)
            self.status.register()

        if enabled is True:
            if self.status.holding is False:
                self.hold()
                self.status.holding = True
            self.status.props.status = StatusNotifier.Status.ACTIVE
        elif self.status:
            if self.status.holding is True:
                self.release()
                self.status.holding = False
            self.status.props.status = StatusNotifier.Status.PASSIVE

    def _init_service(self):
        if self.props.flags & Gio.ApplicationFlags.IS_SERVICE:
            self.hold()

        # FIXME: File system encoding
        def file_changed(monitor, file_changed, other_file, event):
            if not self.settings['watch-downloads-directory']:
                return

            if event != Gio.FileMonitorEvent.CREATED:
                return

            if file_changed.get_basename().rpartition('.')[2] != 'torrent':
                return

            file_uri = file_changed.get_uri()
            logging.info('Got file created event for {}'.format(file_uri))

            self.activate()
            action = self.window.lookup_action('torrent_add')
            action.activate(GLib.Variant('s', file_uri))

        downloads_str = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOWNLOAD)
        if downloads_str:
            downloads = Gio.File.new_for_path(downloads_str)
            self.download_monitor = downloads.monitor_directory(Gio.FileMonitorFlags.NONE)
            self.download_monitor.connect('changed', file_changed)

        self.client = Client(username=self.settings['username'], password=self.settings['password'],
                             hostname=self.settings['hostname'], port=self.settings['port'],
                             tls=self.settings['tls'])

        for prop in ('username', 'password', 'hostname', 'port', 'tls'):
            self.settings.bind(prop, self.client, prop, Gio.SettingsBindFlags.GET)

    def do_open(self, files, n_files, hint):
        self.activate()
        for f in files:
            if f.get_uri_scheme() == 'file':
                self.window.activate_action('torrent_add', GLib.Variant('s', f.get_uri()))
            else:
                self.window.activate_action('torrent_add_uri', GLib.Variant('s', f.get_uri()))

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
        def on_window_destroy(window):
            self.window = None
            self.client.props.timeout = 30 # We can relax the timer if there is no UI

        if not self.window:
            self.window = ApplicationWindow(application=self, client=self.client)
            self.window.connect('destroy', on_window_destroy)
            self.client.props.timeout = 10

        self.window.present()

    def do_shutdown(self):
        Gtk.Application.do_shutdown(self)

    def on_preferences(self, action, param):
        dialog = PreferencesDialog(transient_for=self.window, modal=True, client=self.client)
        dialog.present()

    def on_about(self, action, param):
        about = Gtk.AboutDialog(transient_for=self.window, modal=True,
                                license_type=Gtk.License.GPL_3_0,
                                authors=['Patrick Griffis', ],
                                copyright='Copyright © 2016 Patrick Griffis',
                                logo_icon_name='se.tingping.Trg',
                                version=self.version)
        about.present()

    def _on_open_uri(self, action, param):
        uri = param.get_string()
        Gtk.show_uri_on_window(self.window, uri, Gdk.CURRENT_TIME)
