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

from gi.repository import (
    GLib,
    GObject,
    Gio,
    Soup,
)

from .torrent import Torrent, TorrentStatus
from .timer import Timer

_REFRESH_ALL_LIST = ['id', 'name', 'rateDownload', 'rateUpload', 'eta',
                     'sizeWhenDone', 'percentDone', 'totalSize', 'status',
                     'isFinished', 'trackers', 'downloadDir']


class Client(GObject.Object):
    __gtype_name__ = 'Client'

    __gsignals__ = {

    }

    __gproperties__ = {
        'username': (
            str, _('Username'), _('Username to login with'),
            '',
            GObject.ParamFlags.CONSTRUCT|GObject.ParamFlags.READWRITE,
        ),
        'password': (
            str, _('Password'), _('Password to login with'),
            '',
            GObject.ParamFlags.CONSTRUCT|GObject.ParamFlags.READWRITE,
        ),
        'hostname': (
            str, _('Hostname'), _('Hostname of remote server'),
            'localhost',
            GObject.ParamFlags.CONSTRUCT|GObject.ParamFlags.READWRITE,
        ),
        'port': (
            int, _('Port'), _('Port of remote server'),
            1, GLib.MAXUINT16, 9091,
            GObject.ParamFlags.CONSTRUCT|GObject.ParamFlags.READWRITE,
        ),
        'tls': (
            bool, _('TLS'), _('Connect using HTTPS'),
            False,
            GObject.ParamFlags.CONSTRUCT|GObject.ParamFlags.READWRITE,
        ),
        'torrents': (
            Gio.ListModel, _('Torrents'), _('List of torrents'),
            GObject.ParamFlags.READABLE,
        ),
        'timeout': (
            GObject.TYPE_UINT, _('Timeout'), _('Timer for refreshing torrent list'),
            1, GLib.MAXUINT, 30,
            GObject.ParamFlags.CONSTRUCT|GObject.ParamFlags.READWRITE,
        ),
        'connected': (
            bool, _('Connected'), _('Have successfully connected'),
            False,
            GObject.ParamFlags.CONSTRUCT|GObject.ParamFlags.READWRITE,
        ),
        # These are session properties
        'download-dir': (
            str, _('Download Directory'), _('Directory downloads are saved to'),
            '', GObject.ParamFlags.READABLE
        ),
        'download-dir-free-space': (
            GObject.TYPE_UINT64, _('Free Space'), _('Free space in download directory'),
            0, GLib.MAXUINT64, 0, GObject.ParamFlags.READABLE
        ),
        'alt-speed-enabled': (
            bool, _('Alternate Speed'), _('Alternate speeds enabled'),
            False, GObject.ParamFlags.READABLE
        ),
        # These are session statistics
        'download-speed': (
            GObject.TYPE_UINT64, _('Download Speed'), _('Speed of current downloads'),
            0, GLib.MAXUINT64, 0, GObject.ParamFlags.READABLE
        ),
        'upload-speed': (
            GObject.TYPE_UINT64, _('Upload Speed'), _('Speed of current upload'),
            0, GLib.MAXUINT64, 0, GObject.ParamFlags.READABLE
        ),
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.torrents = Gio.ListStore.new(Torrent)
        self._encoder = TorrentEncoder()
        self._session = Soup.Session.new()
        self._rpc_uri = self._get_rpc_uri()
        self._session_id = '0'
        self._session.connect('authenticate', self._on_authenticate)
        self._refresh_timer = None
        self._session_timer = None

        network_monitor = Gio.NetworkMonitor.get_default()
        network_monitor.connect('network-changed', self._on_network_changed)

        for prop in ('username', 'password'):
            self.connect('notify::' + prop, self._on_credentials_changed)
        for prop in ('hostname', 'port', 'tls'):
            self.connect('notify::' + prop, self._on_server_changed)

        self.alt_speed_enabled = False
        self.download_dir_free_space = 0
        self.download_dir = ''
        self.upload_speed = 0
        self.download_speed = 0

        self._last_auth = (self.username, self.password) # Not ideal
        if self.username and self.password:
            self._session.add_feature_by_type(Soup.AuthBasic)
        self.refresh_all()

    def do_get_property(self, prop):
        return getattr(self, prop.name.replace('-', '_'))

    def do_set_property(self, prop, value):
        setattr(self, prop.name.replace('-', '_'), value)

    def _on_credentials_changed(self, *args):
        new_auth = (self.username, self.password)
        if new_auth != self._last_auth:
            logging.info('Credentials changed')
            self._last_auth = new_auth
            if self.username and self.password:
                self._session.add_feature_by_type(Soup.AuthBasic)
            self.refresh_all(remove=True)

    def _get_rpc_uri(self):
        protocol = 'https' if self.tls else 'http'
        uri = '{}://{}:{}/transmission/rpc'.format(protocol, self.hostname, self.port)
        logging.info('RPC URI set to: {}'.format(uri))
        return uri

    def _on_server_changed(self, *args):
        rpc_uri = self._get_rpc_uri()
        if rpc_uri != self._rpc_uri:
            logging.info('Server information changed')
            self._rpc_uri = rpc_uri
            self._session_id = '0'
            self.refresh_all(remove=True)

    def _on_authenticate(self, session, message, auth, retrying):
        if not retrying and self.username and self.password:
            logging.info('Authenticating as {}'.format(self.username))
            auth.authenticate(self.username, self.password)

    def _on_network_changed(self, monitor, available: bool):
        logging.info('Network status changed to: {}'.format(
            Gio.NetworkConnectivity(monitor.props.connectivity).value_nick
        ))
        # FIXME: More robust localhost check (monitor.can_reach_async)
        if self.hostname == 'localhost':
            return

        if not available:
            self.torrents.remove_all()
            self._refresh_timer.pause()
            self._session_timer.pause()
        else:
            self.refresh_all()

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
            logging.warning('Response was not successful: {} ({})'.format(Soup.Status(status_code).value_name,
                                                                          status_code))
            return

        response_str = message.props.response_body_data.get_data().decode('UTF-8')
        response = json.loads(response_str)
        logging.debug('<<<\n{}'.format(pprint.pformat(response)))

        if response.get('result') != 'success':
            logging.warning('Request failed: {}'.format(response.get('result')))
            return

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

    def session_get(self, callback=None):
        self._make_request_async('session-get', None, callback=callback)

    def session_set(self, arguments, callback=None):
        self._make_request_async('session-set', arguments, callback=callback)

    def session_stats(self, callback=None):
        self._make_request_async('session-stats', None, callback=callback)

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
        def on_add(response):
            new_torrent = response['arguments'].get('torrent-added')
            if new_torrent:
                torrent = Torrent(id=new_torrent['id'], name=new_torrent['name'])
                self.torrents.append(torrent)
                self.torrent_get(new_torrent['id'], _REFRESH_ALL_LIST)
            if callback:
                callback(response)
        self._make_request_async('torrent-add', args, callback=on_add)

    @staticmethod
    def _show_notification(torrent: Torrent):
        notification = Gio.Notification.new(_('Download completed'))
        notification.set_body(torrent.props.name + _(' has finished downloading.'))
        application = Gio.Application.get_default()
        if application and application.settings['notify-on-finish']:
            # TODO: Combine repeated notifications
            application.send_notification(None, notification)

    def _on_refresh_complete(self, response):
        for t in response['arguments']['torrents']:
            for i in range(self.torrents.get_n_items()):
                torrent = self.torrents.get_item(i)
                if torrent.id == t['id']:
                    # If it was downloading but is now seeding or is finished
                    # show a notification
                    if torrent.status == TorrentStatus.DOWNLOAD and \
                       (t['status'] in (TorrentStatus.SEED, TorrentStatus.SEED_WAIT) or t.get('isFinished')):
                        self._show_notification(torrent)
                    torrent.update_from_response(t)
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
        self.session_stats(self._on_refresh_stats_complete)

    def _on_refresh_stats_complete(self, response):
        for prop, value in response['arguments'].items():
            prop_name = Torrent._propertify_name(prop)
            if hasattr(self.props, prop_name):
                setattr(self, prop_name.replace('-', '_'), value)
                self.notify(prop_name)

    def _on_refresh_session_complete(self, response):
        for prop, value in response['arguments'].items():
            if hasattr(self.props, prop):
                setattr(self, prop.replace('-', '_'), value)
                self.notify(prop)

    def _refresh_session(self):
        self.session_get(self._on_refresh_session_complete)

    def _on_refresh_all_complete(self, response):
        self.torrents.remove_all()
        for t in response['arguments']['torrents']:
            torrent = Torrent.new_from_response(t)
            self.torrents.append(torrent)

        if self._refresh_timer is None:
            self._refresh_timer = Timer(self._refresh, timeout=self.timeout)
            self.bind_property('timeout', self._refresh_timer, 'timeout', GObject.BindingFlags.DEFAULT)
        else:
            self._refresh_timer.resume()

        if self._session_timer is None:
            self._session_timer = Timer(self._refresh_session, timeout=300)
        else:
            self._session_timer.resume()

        self.props.connected = True

    def refresh(self):
        """Refresh the list one time in the near future"""
        if self._refresh_timer:
            self._refresh_timer.run_once()

    def refresh_all(self, remove=False):
        if remove:
            self.props.connected = False
            self.torrents.remove_all()
        self.torrent_get(None, _REFRESH_ALL_LIST,
                         callback=self._on_refresh_all_complete)
        if self._refresh_timer:
            # FIXME: Don't want to send too much until we have initial session id
            self.session_stats(self._on_refresh_stats_complete)


class TorrentEncoder(json.JSONEncoder):
    """JSONEncoder that converts Torrent objects into their id's at encode time"""
    def default(self, obj: object) -> str:
        if isinstance(obj, Torrent):
            return obj.id
        else:
            return super().default(obj)
