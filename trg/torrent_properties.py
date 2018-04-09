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
from .torrent_file_view import FileColumn
from .torrent_file import TorrentFileNode
from .gi_composites import GtkTemplate


@GtkTemplate(ui='/se/tingping/Trg/ui/properties.ui')
class TorrentProperties(Gtk.Dialog):
    __gtype_name__ = 'TorrentProperties'

    torrent = GObject.Property(type=Torrent, flags=GObject.ParamFlags.READWRITE|GObject.ParamFlags.CONSTRUCT_ONLY)
    client = GObject.Property(type=Client, flags=GObject.ParamFlags.READWRITE|GObject.ParamFlags.CONSTRUCT_ONLY)
    file_view = GtkTemplate.Child()

    def __init__(self, **kwargs):
        super().__init__(use_header_bar=1, **kwargs)
        self.init_template()
        self.file_view.percent_column.props.visible = True
        self.client.torrent_get(self.torrent, ['files', 'fileStats'], callback=self._on_got_files)

    def _on_got_files(self, response):
        t = response['arguments']['torrents'][0]

        files = t['files']
        file_stats = t['fileStats']
        for i, f in enumerate(files):
            f.update(file_stats[i])

        first_name = files[0]['name']
        if '/' in first_name:
            root_name = first_name.split('/', 1)[0]
            root_node = TorrentFileNode(root_name)

            for i, f in enumerate(files):
                paths = f['name'].rsplit('/')[1:]  # First is skipped since we manually made root
                root_node.add_file(paths, f['length'], i, f['bytesCompleted'],
                                   f['wanted'], f['priority'])
        else:
            root_node = TorrentFileNode(f['name'], f['length'], 0, f['bytesCompleted'],
                                        f['wanted'], f['priority'])

        self.file_view._add_node_to_store(None, root_node)
        self.file_view.expand_all()

    def _get_wanted(self):
        store = self.file_view.torrent_file_store
        files_wanted = []
        files_unwanted = []
        pri_high = []
        pri_norm = []
        pri_low = []

        def iterate_model(_iter):
            while _iter is not None:
                if store.iter_has_child(_iter):
                    iterate_model(store.iter_children(_iter))
                else:
                    row = store[_iter]
                    index = row[FileColumn.index]

                    if row[FileColumn.pri_val] == -1:
                        pri_low.append(index)
                    elif row[FileColumn.pri_val] == 0:
                        pri_norm.append(index)
                    elif row[FileColumn.pri_val] == 1:
                        pri_high.append(index)

                    if row[FileColumn.download]:
                        files_wanted.append(index)
                    else:
                        files_unwanted.append(index)

                _iter = store.iter_next(_iter)

        iterate_model(store.get_iter_first())
        args = {}  # TODO: Empty list is shorthand for all
        if files_wanted:
            args['files-wanted'] = files_wanted
        if files_unwanted:
            args['files-unwanted'] = files_unwanted
        if pri_high:
            args['priority-high'] = pri_high
        if pri_norm:
            args['priority-norm'] = pri_norm
        if pri_low:
            args['priority-low'] = pri_low
        return args

    def do_response(self, response):
        if response == Gtk.ResponseType.APPLY:
            args = self._get_wanted()
            if args:
                print(args)
                self.client.torrent_set(self.torrent, args)

        if response != Gtk.ResponseType.DELETE_EVENT:
            self.destroy()
