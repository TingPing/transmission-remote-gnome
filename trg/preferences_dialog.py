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

import copy
import logging
from os import path
from contextlib import suppress
from collections import namedtuple
from gettext import gettext as _
from gi.repository import (
    GLib,
    GObject,
    Gio,
    Gtk,
)

from .gi_composites import GtkTemplate
from .client import Client


_is_flatpak = None


def _get_is_flatpak():
    global _is_flatpak
    if _is_flatpak is None:
        file_ = path.join(GLib.get_user_runtime_dir(), 'flatpak-info')
        _is_flatpak = path.exists(file_)
    return _is_flatpak


def _get_has_statusnotifier():
    try:
        from gi.repository import StatusNotifier
        return True
    except ImportError:
        return False


Row = namedtuple('Row', ('title', 'widget', 'bind_property', 'setting'))
ToggledRow = namedtuple('ToggledRow', ('title', 'widget', 'bind_property',
                                       'setting', 'toggle_setting'))
Page = namedtuple('Page', ('id', 'title', 'rows'))


@GtkTemplate(ui='/se/tingping/Trg/ui/preferencesdialog.ui')
class PreferencesDialog(Gtk.Dialog):
    __gtype_name__ = 'PreferencesDialog'

    local_stack = GtkTemplate.Child()
    remote_stack = GtkTemplate.Child()
    remote_page_stack = GtkTemplate.Child()
    remote_page_box = GtkTemplate.Child()
    disconnected_page = GtkTemplate.Child()
    client = GObject.Property(type=Client, flags=GObject.ParamFlags.CONSTRUCT_ONLY|GObject.ParamFlags.READWRITE)

    def __init__(self, **kwargs):
        super().__init__(use_header_bar=1, **kwargs)
        self.init_template()

        # ---------- Local Settings --------------
        self.settings = Gio.Settings.new('se.tingping.Trg')

        local_pages = (
            Page('connection', _('Connection'), (
                Row(_('Hostname'), Gtk.Entry.new(), 'text', 'hostname'),
                Row(_('Port'), Gtk.SpinButton.new_with_range(0, GLib.MAXUINT16, 1), 'value', 'port'),
                Row(_('Username'), Gtk.Entry.new(), 'text', 'username'),
                Row(_('Password'), Gtk.Entry(visibility=False, input_purpose=Gtk.InputPurpose.PASSWORD), 'text',
                    'password'),
                Row(_('Connect over HTTPS'), Gtk.Switch.new(), 'active', 'tls'),
            )),
            Page('service', _('Service'), [
                Row(_('Automatically Load Torrent Files'), Gtk.Switch.new(), 'active',
                    'watch-downloads-directory'),
                Row(_('Show Notifications on Completion'), Gtk.Switch.new(), 'active',
                    'notify-on-finish'),
            ]),
        )
        if not _get_is_flatpak():
            self._autostart_switch = AutoStartSwitch()
            as_row = Row(_('Autostart service on login'), self._autostart_switch, '', '')
            local_pages[1].rows.append(as_row)

        if _get_has_statusnotifier():
            row = Row(_('Show status icon'), Gtk.Switch.new(), 'active', 'show-status-icon')
            local_pages[1].rows.append(row)

        bind_flags = Gio.SettingsBindFlags.DEFAULT|Gio.SettingsBindFlags.NO_SENSITIVITY
        self._create_settings_pane(local_pages, self.local_stack,
                                   lambda wid, prop, setting: self.settings.bind(setting, wid, prop, bind_flags))

        # ------------- Remote Page ---------------
        self.remote_settings = RemoteSettings(self.client)
        encryption_combo = Gtk.ComboBoxText.new()
        for val in (('required', _('Required')), ('preferred', _('Preferred')), ('tolerated', _('Tolerated'))):
            encryption_combo.append(*val)

        remote_pages = (
            Page('general', _('General'), (
                Row(_('Download Directory'), Gtk.Entry.new(), 'text', 'download-dir'),
                ToggledRow(_('Incomplete Directory'), Gtk.Entry.new(), 'text',
                           'incomplete-dir', 'incomplete-dir-enabled'),
                Row(_('Append ".part" to Incomplete'), Gtk.Switch.new(), 'active', 'rename-partial-files'),
            )),
            Page('connections', _('Connection'), (
                Row(_('Peer Port'), Gtk.SpinButton.new_with_range(0, GLib.MAXUINT16, 1), 'value', 'peer-port'),
                Row(_('Encryption'), encryption_combo, 'active-id', 'encryption'),
                ToggledRow(_('Blocklist URL'), Gtk.Entry.new(), 'text',
                           'blocklist-url', 'blocklist-enabled'),
                Row(_('Randomize Port on Start'), Gtk.Switch.new(), 'active', 'peer-port-random-on-start'),
                Row(_('DHT'), Gtk.Switch.new(), 'active', 'dht-enabled'),
                Row(_('Peer Exchange'), Gtk.Switch.new(), 'active', 'pex-enabled'),
                Row(_('Local Peer Discovery'), Gtk.Switch.new(), 'active', 'lpd-enabled'),
                Row(_('UTP'), Gtk.Switch.new(), 'active', 'utp-enabled'),
                Row(_('UPNP'), Gtk.Switch.new(), 'active', 'port-forwarding-enabled'),

            )),
            # TODO: Add headers
            # TODO: Add toggles for these
            Page('limits', _('Limits'), (
                ToggledRow(_('Download Limit (KB/s)'), Gtk.SpinButton.new_with_range(0, GLib.MAXUINT32, 1),
                           'value', 'speed-limit-down', 'speed-limit-down-enabled'),
                ToggledRow(_('Upload Limit (KB/s)'), Gtk.SpinButton.new_with_range(0, GLib.MAXUINT32, 1),
                           'value', 'speed-limit-up', 'speed-limit-up-enabled'),
                ToggledRow(_('Seed Ratio Limit'), Gtk.SpinButton.new_with_range(0, GLib.MAXUINT16, .1),
                           'value', 'seedRatioLimit', 'seedRatioLimited'),
                ToggledRow(_('Download Queue Size'), Gtk.SpinButton.new_with_range(0, GLib.MAXUINT16, 1),
                           'value', 'download-queue-size', 'download-queue-enabled'),
                ToggledRow(_('Seed Queue Size'), Gtk.SpinButton.new_with_range(0, GLib.MAXUINT16, 1),
                           'value', 'seed-queue-size', 'seed-queue-enabled'),
                ToggledRow(_('Idle Seed Queue Size'), Gtk.SpinButton.new_with_range(0, GLib.MAXUINT16, 1),
                           'value', 'idle-seeding-limit', 'idle-seeding-limit-enabled'),
                Row(_('Global Peer Limit'), Gtk.SpinButton.new_with_range(0, GLib.MAXUINT16, 1),
                    'value', 'peer-limit-global',),
                Row(_('Per-Torrent Peer Limit'), Gtk.SpinButton.new_with_range(0, GLib.MAXUINT16, 1),
                    'value', 'peer-limit-per-torrent',),
            )),
            Page('alt-limits', _('Alternate Limits'), (
                Row(_('Alternative Limits Active'), Gtk.Switch.new(), 'active', 'alt-speed-enabled'),
                Row(_('Alternate Down Limit (KB/s)'), Gtk.SpinButton.new_with_range(0, GLib.MAXUINT32, 1),
                    'value', 'alt-speed-down'),
                Row(_('Alternate Up Limit (KB/s)'), Gtk.SpinButton.new_with_range(0, GLib.MAXUINT32, 1),
                    'value', 'alt-speed-up'),
                # TODO: Alt-time limits
            )),
        )

        self._create_settings_pane(remote_pages, self.remote_stack, self.remote_settings.bind_setting)
        if not self.client.props.connected:  # TODO: Handle connection changes
            self.remote_page_stack.props.visible_child = self.disconnected_page
        else:
            self.remote_settings.refresh(self._on_remote_settings_refresh)

    def _on_remote_settings_refresh(self):
        self.remote_page_stack.props.visible_child = self.remote_page_box

    def _create_settings_pane(self, pages, stack, bind_func):
        for page in pages:
            id_, title, rows = page
            grid = Gtk.Grid(visible=True, margin=18,
                            column_spacing=12, row_spacing=6)
            for i, row in enumerate(rows):
                label = Gtk.Label(label=row.title, halign=Gtk.Align.END, visible=True)
                label.get_style_context().add_class('dim-label')
                row.widget.props.hexpand = True
                row.widget.show()
                grid.attach(label, 0, i, 1, 1)

                if isinstance(row, ToggledRow):
                    widget = Gtk.Box(visible=True, spacing=6)
                    toggle = Gtk.Switch(visible=True, valign=Gtk.Align.CENTER)
                    bind_func(toggle, 'active', row.toggle_setting)
                    toggle.bind_property('active', row.widget, 'sensitive',
                                         GObject.BindingFlags.SYNC_CREATE)
                    widget.add(toggle)
                    widget.add(row.widget)
                else:
                    widget = row.widget
                if isinstance(widget, Gtk.Switch):
                    widget.props.halign = Gtk.Align.START
                grid.attach(widget, 1, i, 1, 1)

                if row.bind_property and row.setting:
                    bind_func(row.widget, row.bind_property, row.setting)
            stack.add_titled(grid, id_, title)

    def do_show(self):
        Gtk.Dialog.do_show(self)
        self.settings.delay()

    def do_response(self, response_id):
        if response_id == Gtk.ResponseType.APPLY:
            self.settings.apply()
            self.remote_settings.apply()
            if not _get_is_flatpak():
                self._autostart_switch.apply()
        else:
            self.settings.revert()

        if response_id != Gtk.ResponseType.DELETE_EVENT:
            self.destroy()


class RemoteSettings:
    def __init__(self, client):
        self.client = client
        self.settings = {}  # Settings and their values
        self.settings_map = {}  # Maps settings to their widgets

    def _on_property_change(self, widget, pspec, userdata):
        prop, setting = userdata
        self.settings[setting] = getattr(widget.props, prop)

    def bind_setting(self, widget: Gtk.Widget, prop: str, setting: str):
        widget.connect('notify::' + prop, self._on_property_change, (prop, setting))
        self.settings_map[setting] = (widget, prop)
        self.settings[setting] = None

    def refresh(self, callback):
        def on_refresh(response):
            for setting, value in response['arguments'].items():
                if setting in self.settings_map:
                    self.settings[setting] = value

                    wid, prop = self.settings_map[setting]
                    setattr(wid.props, prop, value)

            self._old_settings = copy.copy(self.settings)
            callback()
        self.client.session_get(callback=on_refresh)

    def apply(self):
        if hasattr(self, '_old_settings'):  # May not have gotten them yet
            changed_settings = {k: v for k, v in self.settings.items() if v != self._old_settings[k]}
            self.client.session_set(changed_settings)


class AutoStartSwitch(Gtk.Switch):
    def __init__(self, **kwargs):
        super().__init__(sensitive=False, **kwargs)
        self._was_enabled = None

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
            self._was_enabled = True
            logging.debug('Autostart file exists')
        except GLib.Error as e:
            self.props.active = False
            self._was_enabled = False
            logging.debug('Querying autostart file returned: {}'.format(e))
        self.props.sensitive = True

    def apply(self):
        """Creates or deletes the autostart file based upon current state"""
        if not self.props.sensitive: # We never got the current state
            return

        if self.props.active and not self._was_enabled:
            logging.info('Creating autostart file')
            source = Gio.File.new_for_uri('resource:///se/tingping/Trg/se.tingping.Trg.service.desktop')
            if hasattr(source, 'copy_async'):
                # TODO: Fix upstream in GLib
                source.copy_async(self.autostart_file, Gio.FileCopyFlags.NONE, GLib.PRIORITY_DEFAULT)
            else:
                with suppress(GLib.Error):
                    source.copy(self.autostart_file, Gio.FileCopyFlags.NONE)
        elif not self.props.active and self._was_enabled:
            logging.info('Deleting autostart file')
            self.autostart_file.delete_async(GLib.PRIORITY_DEFAULT)
