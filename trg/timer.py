# timer.py
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
from gi.repository import GLib, GObject


class Timer(GObject.Object):
	"""Dynamic timer that allows dynamically changing frequency"""
	timeout = GObject.Property(type=GObject.TYPE_UINT)

	def __init__(self, function, **kwargs):
		super().__init__(**kwargs)
		assert (callable(function))

		self._func = function
		self._id = 0

		self._add_timeout()
		self.connect('notify::timeout', self._on_timeout_changed)

	def __del__(self):
		logging.debug('Timer removed')
		if self._id:
			GLib.source_remove(self._id)

	def _add_timeout(self):
		if self._id:
			GLib.source_remove(self._id)
		self._id = GLib.timeout_add_seconds(self.timeout, self._run_func)

	def _on_timeout_changed(self, prop, param):
		logging.debug('Timeout changed')
		self._add_timeout()

	def _run_func(self):
		try:
			logging.debug('Timer running')
			self._func()
		except Exception as e:
			logging.exception(e)

		return GLib.SOURCE_CONTINUE

	def run_once(self):
		# To be the most efficient we will restart the timer from here
		GLib.source_remove(self._id)
		self._id = 0

		def run_real():
			self._run_func()
			self._add_timeout()
			return GLib.SOURCE_REMOVE

		# FIXME: The timing of this is wrong but logically all of our HTTP calls are in the correct order
		# the server just doesn't respond with the up to date information for some actions
		GLib.timeout_add(250, run_real)
