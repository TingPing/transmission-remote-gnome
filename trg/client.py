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

	def _on_message_finish(self, session, message, user_data=None):
		status_code = message.props.status_code
		logging.debug('Got response code: {} ({})'.format(Soup.Status(status_code).value_name, status_code))

		if status_code == Soup.Status.UNAUTHORIZED:
			if not self.username or not self.password:
				logging.warning('Requires authentication')
			else:
				logging.warning('Failed to log in as {}'.format(self.username))
		elif status_code == Soup.Status.CONFLICT:
			self._session_id = message.props.response_headers.get('X-Transmission-Session-Id')
			logging.info('Got new session id ({}), retrying'.format(self._session_id))
			message.props.request_headers.replace('X-Transmission-Session-Id', self._session_id)
			# requeue_message fails?
			self._session.cancel_message(message, Soup.Status.CANCELLED)
			self._session.queue_message(message, self._on_message_finish, user_data=user_data)

		if not 200 <= status_code < 300:
			logging.warning('Response was not successful: {} ({})'.format(Soup.Status(status_code).value_name, status_code))
			return

		response_str = message.props.response_body_data.get_data().decode('UTF-8')
		response = json.loads(response_str)
		# logging.debug('<<<\n{}'.format(pprint.pformat(response)))

		if user_data:
			user_data(response)

	def _make_request_async(self, method, arguments=None, callback=None, tag=None):
		message = Soup.Message.new('POST', self._rpc_uri)
		message.props.request_headers.append('X-Transmission-Session-Id', self._session_id)

		request = {'method': method}
		if arguments:
			request['arguments'] = arguments
		if tag:
			request['tag'] = tag

		logging.debug('>>>\n{}'.format(pprint.pformat(request)))
		message.set_request('application/json', Soup.MemoryUse.COPY,
		                    bytes(self._encoder.encode(request), 'UTF-8'))

		self._session.queue_message(message, self._on_message_finish, user_data=callback)

	@staticmethod
	def _make_args(torrent, **kwargs):
		args = kwargs.pop('args', {})
		if torrent is not None:
			if isinstance(torrent, str) and torrent != 'recently-active':
				logging.error('Invalid torrent sent')
			args['ids'] = torrent
		for k, v in kwargs.items():
			if v is not None:
				args[k] = v
		return args

	def torrent_start(self, torrent):
		"""
		:type torrent: List of Torrent, single Torrent, None, or 'recently-active'
		"""
		self._make_request_async('torrent-start', self._make_args(torrent))

	def torrent_stop(self, torrent):
		self._make_request_async('torrent-stop', self._make_args(torrent))

	def torrent_verify(self, torrent):
		self._make_request_async('torrent-verify', self._make_args(torrent))

	def torrent_reannounce(self, torrent):
		self._make_request_async('torrent-reannounce', self._make_args(torrent))

	def torrent_remove(self, torrent, delete_data=False):
		args = {'delete-local-data': delete_data}
		self._make_request_async('torrent-remove', self._make_args(torrent, args=args))

	def torrent_set(self, torrent, args):
		self._make_request_async('torrent-set', self._make_args(torrent, args=args))

	def torrent_get(self, torrent, fields, callback=None):
		args = self._make_args(torrent, fields=fields)
		self._make_request_async('torrent-get', args, callback=callback)

	def torrent_move(self, torrent, location: str, move=None):
		args = self._make_args(torrent, location=location, move=move)
		self._make_request_async('torrent-set-location', args)

	def torrent_rename(self, torrent, path: str, name: str):
		args = self._make_args(torrent, path=path, name=name)
		self._make_request_async('torrent-rename-path', args)

	def torrent_add(self, args, callback=None):
		self._make_request_async('torrent-add', args, callback=callback)

	def _show_notification(self, torrent: Torrent):
		notification = Gio.Notification.new(_('Download completed'))
		notification.set_body(torrent.props.name + _('has finished.'))
		application = Gio.Application.get_default()
		if application and application.settings['notify-on-finish']:
			# TODO: Combine repeated notifications
			application.send_notification(None, notification)

	def _on_refresh_complete(self, response):
		for t in response['arguments']['torrents']:
			for i in range(self.torrents.get_n_items()):
				torrent = self.torrents.get_item(i)
				if torrent.id == t['id']:
					torrent.update_from_response(t)
					if t.get('isFinished'):
						self._show_notification(torrent)
					break
			else:
				torrent = Torrent.new_from_response(t)
				self.torrents.append(torrent)

		for t in response['arguments']['removed']:
			for i in range(self.torrents.get_n_items() - 1, 0, -1):
				if self.torrents.get_item(i).id == t:
					self.torrents.remove(i)

	def _refresh(self):
		self.torrent_get('recently-active', ['id', 'name', 'rateDownload', 'rateUpload', 'eta',
		                                     'sizeWhenDone', 'percentDone', 'totalSize', 'status',
		                                     'isFinished'],
						 callback=self._on_refresh_complete)
		return GLib.SOURCE_CONTINUE

	def _on_refresh_all_complete(self, response):
		self.torrents.remove_all()
		for t in response['arguments']['torrents']:
			torrent = Torrent.new_from_response(t)
			self.torrents.append(torrent)

		if self._refresh_timer:
			GLib.source_remove(self._refresh_timer)

		self._refresh_timer = GLib.timeout_add_seconds(20, self._refresh)

	def refresh_all(self):
		self.torrent_get(None, ['id', 'name', 'rateDownload', 'rateUpload', 'eta',
								'sizeWhenDone', 'percentDone', 'totalSize', 'status',
								'isFinished'],
						 callback=self._on_refresh_all_complete)


class TorrentEncoder(json.JSONEncoder):
	"""JSONEncoder that converts Torrent objects into their id's at encode time"""
	def default(self, obj: object) -> str:
		if isinstance(obj, Torrent):
			return obj.id
		else:
			return super().default(obj)
