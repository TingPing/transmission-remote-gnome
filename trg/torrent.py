# torrent.py
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
from enum import IntEnum
import os

from gi.repository import (
    GLib,
    GObject,
    Gio,
)

from .tracker import Tracker


class TorrentFile(GObject.Object):
    __gtype_name__ = 'TorrentFile'

    bytes_completed = GObject.Property(type=int)
    length = GObject.Property(type=int)
    name = GObject.Property(type=str)
    wanted = GObject.Property(type=bool, default=True)
    priority = GObject.Property(type=int)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<TorrentFile "{}">'.format(self.name)


class Torrent(GObject.Object):
    __gtype_name__ = 'Torrent'

    __gproperties__ = {
        'id': (
            GObject.TYPE_UINT, _('ID'), _('Unique torrent identifier'),
            0, GLib.MAXUINT, 0,
            GObject.ParamFlags.CONSTRUCT_ONLY|GObject.ParamFlags.READWRITE,
        ),
        'name': (
            str, _('Name'), _('Name of torrent'), '',
            GObject.ParamFlags.CONSTRUCT|GObject.ParamFlags.READWRITE,
        ),
        'download-dir': (
            str, _('Directory'), _('Download Directory'), '',
            GObject.ParamFlags.CONSTRUCT | GObject.ParamFlags.READWRITE,
        ),
        'eta': (
            GObject.TYPE_INT64, _('Eta'), _('Time to finish'),
            GLib.MININT64, GLib.MAXINT64, 0,
            GObject.ParamFlags.CONSTRUCT|GObject.ParamFlags.READWRITE,
        ),
        'files': (
            Gio.ListModel, _('Files'), _('List of files'),
            GObject.ParamFlags.CONSTRUCT|GObject.ParamFlags.READWRITE,
        ),
        'size-when-done': (
            GObject.TYPE_UINT64, _('Size when done'), _('Total size when finished'),
            0, GLib.MAXUINT64, 0,
            GObject.ParamFlags.CONSTRUCT|GObject.ParamFlags.READWRITE,
        ),
        'total-size': (
            GObject.TYPE_UINT64, _('Size'), _('Total size of torrent'),
            0, GLib.MAXUINT64, 0,
            GObject.ParamFlags.CONSTRUCT|GObject.ParamFlags.READWRITE,
        ),
        'rate-download': (
            GObject.TYPE_UINT64, _('Download Rate'), _('Download speed in bytes/s'),
            0, GLib.MAXUINT64, 0,
            GObject.ParamFlags.CONSTRUCT|GObject.ParamFlags.READWRITE,
        ),
        'rate-upload': (
            GObject.TYPE_UINT64, _('Upload Rate'), _('Upload speed in bytes/s'),
            0, GLib.MAXUINT64, 0,
            GObject.ParamFlags.CONSTRUCT|GObject.ParamFlags.READWRITE,
        ),
        'percent-done': (
            float, _('Percent Done'), _('Percentage completed'),
            0.0, 1.0, 0.0,
            GObject.ParamFlags.CONSTRUCT|GObject.ParamFlags.READWRITE,
        ),
        'status': (
            GObject.TYPE_UINT64, _('Status'), _('Current status of torrent'),
            0, GLib.MAXUINT64, 0,
            GObject.ParamFlags.CONSTRUCT|GObject.ParamFlags.READWRITE,
        ),
        'error': (
            GObject.TYPE_UINT64, _('Error'), _('Error code of torrent'),
            0, GLib.MAXUINT64, 0,
            GObject.ParamFlags.CONSTRUCT|GObject.ParamFlags.READWRITE,
        ),
        'is-finished': (
            bool, _('Finished'), _('Torrent is finished downloading'), False,
            GObject.ParamFlags.CONSTRUCT|GObject.ParamFlags.READWRITE,
        ),
        'trackers': (
            Gio.ListModel, _('Trackers'), _('List of trackers'),
            GObject.ParamFlags.CONSTRUCT|GObject.ParamFlags.READWRITE,
        ),
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.files = Gio.ListStore.new(TorrentFile)
        self.trackers = Gio.ListStore.new(Tracker)

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<Torrent {}>'.format(self.id)

    @staticmethod
    def _propertify_name(name: str) -> str:
        """Converts a transmission property name to a gobject style one"""
        prop_name = ''
        for c in name:
            if c.isupper():
                prop_name += '-'
                prop_name += c.lower()
            else:
                prop_name += c
        return prop_name

    @staticmethod
    def _propertify_dict(d: dict) -> dict:
        prop_dict = {}
        for k, v in d.items():
            prop_dict[Torrent._propertify_name(k)] = v
        return prop_dict

    def update_from_response(self, response: dict):
        for k, v in response.items():
            if k != 'id':
                prop = self._propertify_name(k)
                if getattr(self.props, prop) != v:
                    logging.debug('Updating {} of torrent {}'.format(k, self))
                    setattr(self.props, prop, v)

    @classmethod
    def new_from_response(cls, response: dict):
        # TODO: Generic solution to lists
        files = response.pop('files', None)
        trackers = response.pop('trackers', None)
        prop_dict = Torrent._propertify_dict(response)
        torrent = cls(**prop_dict)
        if files:
            torrent.set_files(files)
        if trackers:
            torrent._set_trackers(trackers)
        return torrent

    @property
    def uri(self):
        if self.files.get_n_items() <= 1:
            # FIXME: This is kinda a workaround for my usage
            # which is opening a flatpak and the file isn't working
            path = self.download_dir
        else:
            path = os.path.join(self.download_dir, self.name)
        return Gio.File.new_for_path(path).get_uri()

    def set_files(self, files: list):
        self.files.remove_all()
        for d in files:
            prop_dict = self._propertify_dict(d)
            f = TorrentFile(**prop_dict)
            self.files.append(f)

    def _set_trackers(self, trackers: list):
        self.trackers.remove_all()
        for d in trackers:
            prop_dict = self._propertify_dict(d)
            t = Tracker(**prop_dict)
            self.trackers.append(t)

    def do_get_property(self, prop):
        return getattr(self, prop.name.replace('-', '_'))

    def do_set_property(self, prop, value):
        setattr(self, prop.name.replace('-', '_'), value)


class TorrentStatus(IntEnum):
    STOPPED = 0
    CHECK_WAIT = 1
    CHECK = 2
    DOWNLOAD_WAIT = 3
    DOWNLOAD = 4
    SEED_WAIT = 5
    SEED = 6


class TorrentError(IntEnum):
    OK = 0
    TRACKER_WARNING = 1
    TRACKER_ERROR = 2
    LOCAL_ERROR = 3
