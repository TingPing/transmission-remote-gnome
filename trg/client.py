# client.py
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

import json
import pprint
import logging
from gettext import gettext as _

import gi
gi.require_version('Soup', '2.4')
from gi.repository import (
	GLib,
    GObject,
	Gio,
    Soup,
)

from .torrent import Torrent


class Client(GObject.Object):
	__gtype_name__ = 'Client'

	__gsignals__ = {

	}

	__gproperties__ = {
		'username': (
		    str, _('Username'), _('Username to login with'),
			'',
			GObject.ParamFlags.CONSTRUCT_ONLY|GObject.ParamFlags.READWRITE,
		),
		'password': (
		    str, _('Password'), _('Password to login with'),
			'',
			GObject.ParamFlags.CONSTRUCT_ONLY|GObject.ParamFlags.READWRITE,
		),
		'hostname': (
		    str, _('Hostname'), _('Hostname of remote server'),
			'localhost',
			GObject.ParamFlags.CONSTRUCT_ONLY|GObject.ParamFlags.READWRITE,
		),
		'port': (
		    int, _('Port'), _('Port of remote server'),
			1, GLib.MAXUINT16, 9091,
			GObject.ParamFlags.CONSTRUCT_ONLY|GObject.ParamFlags.READWRITE,
		),

		'torrents': (
		    Gio.ListModel, _('Torrents'), _('List of torrents'),
			GObject.ParamFlags.READABLE,
		),
	}

	def __init__(self, **kwargs):
		super().__init__(**kwargs)
		self.torrents = Gio.ListStore.new(Torrent)
		self._encoder = TorrentEncoder()
		self._session = Soup.Session.new()
		self._rpc_uri = 'http://{}:{}/transmission/rpc'.format(self.hostname, self.port)
		self._session_id = '0'
		self._session.connect('authenticate', self._on_authenticate)
		self._refresh_timer = 0

		if self.username and self.password:
			self._session.add_feature_by_type(Soup.AuthBasic)

	def __del__(self):
		if self._refresh_timer:
			GLib.source_remove(self._refresh_timer)

	def do_get_property(self, prop):
		return getattr(self, prop.name)

	def do_set_property(self, prop, value):
		setattr(self, prop.name, value)

	def _on_authenticate(self, session, message, auth, retrying):
		if not retrying and self.username and self.password:
			logging.info('Authenticating as {}'.format(self.username))
			auth.authenticate(self.username, self.password)

	def _make_request(self, method, arguments=None, tag=None):
		message = Soup.Message.new('POST', self._rpc_uri)
		message.props.request_headers.append('X-Transmission-Session-Id', self._session_id)

		request = { 'method': method }
		if arguments:
			request['arguments'] = arguments
		if tag:
			requests['tag'] = tag

		logging.debug('>>>\n{}'.format(pprint.pformat(request)))
		message.set_request('application/json', Soup.MemoryUse.COPY,
		                    bytes(self._encoder.encode(request), 'UTF-8'))

		# TODO: Async
		ret = self._session.send_message(message)
		logging.debug('Got response code: {}'.format(ret))

		if ret == Soup.Status.UNAUTHORIZED:
			if not self.username or not self.password:
				logging.warning('Requires authentication')
			else:
				logging.warning('Failed to log in as {}'.format(self.username))
			return {}
		elif ret == Soup.Status.CONFLICT:
			self._session_id = message.props.response_headers.get('X-Transmission-Session-Id')
			logging.info('Got new session id ({}), retrying'.format(self._session_id))
			return self._make_request(method, arguments, tag)

		if not 200 <= ret < 300:
			logging.warning('Response was not successful: {}'.format(ret))
			return {}

		response_str = message.props.response_body_data.get_data().decode('UTF-8')
		response = json.loads(response_str)
		logging.debug('<<<\n{}'.format(pprint.pformat(response)))
		return response

	@staticmethod
	def _make_args(torrent, **kwargs):
		args = kwargs.pop('args', {})
		if torrent is not None:
			if isinstance(torrent, str) and torrent != 'recently-active':
				logging.error('Invalid torrent sent')
			args['ids'] = torrent
		for k,v in kwargs.items():
			if v is not None:
				args[k] = v
		return args

	def torrent_start(self, torrent):
		'''
		:type torrent: List of Torrent, single Torrent, None, or 'recently-active'
		'''
		self._make_request('torrent-start', self._make_args(torrent))

	def torrent_set(self, torrent, args):
		self._make_request('torrent-set', self._make_args(torrent, args=args))

	def torrent_get(self, torrent, fields):
		args = self._make_args(torrent, fields=fields)
		return self._make_request('torrent-get', args)

	def torrent_move(self, torrent, location:str, move=None):
		args = self._make_args(torrent, location=location, move=move)
		self._make_request('torrent-set-location', )

	def torrent_rename(self, torrent, path:str, name:str):
		args = self._make_args(torrent, path=location, name=name)
		self._make_request('torrent-rename-path', args)

	def torrent_add(self, args):
		return self._make_request('torrent-add', args)

	def _refresh(self):
		response = self.torrent_get('recently-active', ['id', 'name', 'rateDownload', 'rateUpload', 'eta',
		                                   'sizeWhenDone', 'percentDone', 'totalSize'])

		if not response:
			return GLib.SOURCE_CONTINUE

		for t in response['arguments']['torrents']:
			for i in range(self.torrents.get_n_items()):
				if self.torrents.get_item(i).id == t['id']:
					break
			else:
				torrent = Torrent.new_from_response(t)
				self.torrents.append(torrent)

		for t in response['arguments']['removed']:
			for i in range(self.torrents.get_n_items() - 1, 0, -1):
				if self.torrents.get_item(i).id == t:
					self.torrents.remove(i)

		return GLib.SOURCE_CONTINUE

	def refresh_all(self):
		response = self.torrent_get(None, ['id', 'name', 'rateDownload', 'rateUpload', 'eta',
		                                   'sizeWhenDone', 'percentDone', 'totalSize'])
		self.torrents.remove_all()
		for t in response['arguments']['torrents']:
			torrent = Torrent.new_from_response(t)
			self.torrents.append(torrent)

		if self._refresh_timer:
			GLib.source_remove(self._refresh_timer)

		self._refresh_timer = GLib.timeout_add_seconds(20, self._refresh)

class TorrentEncoder(json.JSONEncoder):
	'''JSONEncoder that converts Torrent objects into their id's at encode time'''
	def default(self, obj):
		if isinstance(obj, Torrent):
			return obj.id
		else:
			return super().default(obj)
