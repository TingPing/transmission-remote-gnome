# torrent_properties.py
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

from gi.repository import (
    GObject,
    Gtk,
)
from .torrent import Torrent
from .client import Client
from .gi_composites import GtkTemplate


@GtkTemplate(ui='/se/tingping/Trg/ui/properties.ui')
class TorrentProperties(Gtk.Dialog):
    __gtype_name__ = 'TorrentProperties'

    torrent = GObject.Property(type=Torrent, flags=GObject.ParamFlags.READWRITE|GObject.ParamFlags.CONSTRUCT_ONLY)
    client = GObject.Property(type=Client, flags=GObject.ParamFlags.READWRITE|GObject.ParamFlags.CONSTRUCT_ONLY)

    def __init__(self, **kwargs):
        super().__init__(use_header_bar=1, **kwargs)
        self.init_template()

    def do_response(self, response):
        if response != Gtk.ResponseType.DELETE_EVENT:
            self.destroy()
