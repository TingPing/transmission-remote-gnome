# torrent_file.py
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

from . import bencode

from gi.repository import (
	GLib,
	GObject,
	Gio,
)


class TorrentFileNode:
	def __init__(self, name: str, size: int=-1, index: int=-1):
		self.name = name
		self.size = size
		self.index = index # Used by transmission

		self.children = [] # List of nodes

	def get_size(self):
		if self.size >= 0:
			return self.size
		else:
			return sum(child.get_size() for child in self.children)

	def add_file(self, paths: list, size: int, index: int):
		n = self
		filenode = TorrentFileNode(paths.pop(), size, index)
		for path in paths:
			for child in n.children:
				if child.name == path:
					n = child
					break
			else:
				new_child = TorrentFileNode(path)
				n.children.append(new_child)
				n = new_child

		n.children.append(filenode)


class TorrentFile(GObject.Object):
	__gtype_name__ = 'TrgTorrentFile'

	__gsignals__ = {
		'file-loaded': (GObject.SIGNAL_RUN_FIRST, None, ()),
		'file-invalid': (GObject.SIGNAL_RUN_FIRST, None, (str, )),
	}

	rwc_flags = GObject.ParamFlags.CONSTRUCT_ONLY|GObject.ParamFlags.READWRITE
	uri = GObject.Property(type=str, flags=rwc_flags)
	cancellable = GObject.Property(type=Gio.Cancellable, flags=rwc_flags)

	def __init__(self, **kwargs):
		super().__init__(**kwargs)

		self.files = None
		self.base64 = b''

		self.file = Gio.File.new_for_uri(self.uri)
		assert (self.file.get_uri_scheme() == 'file')
		self.file.load_contents_async(self.cancellable, self._on_contents_loaded)

	@staticmethod
	def new_for_uri(uri, cancellable):
		return TorrentFile(uri=uri, cancellable=cancellable)

	def _parse_data(self, data: bytes):
		"""Converts the dictionary of metadata into a tree of files"""
		try:
			data_dict = bencode.decode(data)
			info = data_dict[b'info']
			if b'files' in info:
				directory = info[b'name'].decode('UTF-8')
				self.files = TorrentFileNode(directory)
				files = info[b'files']
				for i, d in enumerate(files):
					utf8_paths = [path.decode('UTF-8') for path in d[b'path']]
					self.files.add_file(utf8_paths, d[b'length'], i)
			else:
				filename = info[b'name'].decode('UTF-8')
				self.files = TorrentFileNode(filename, info[b'length'], index=0)

			self.emit('file-loaded')

		except bencode.DecodingError as e:
			self.emit('file-invalid', 'Failed to decode file: {}'.format(e))
		except UnicodeError as e:
			self.emit('file-invalid', 'Failed to decode UTF-8: {}'.format(e))
		except KeyError as e:
			self.emit('file-invalid', 'Failed to get information from file: {}'.format(e))

	def _on_contents_loaded(self, file, result):
		try:
			_, bdata, _ = file.load_contents_finish(result)
		except GLib.Error as e:
			self.emit('file-invalid', 'Failed load file contents: {}'.format(e.msg))
			return

		self.base64 = GLib.base64_encode(bdata)
		self._parse_data(bdata)

	def get_base64(self):
		return self.base64
