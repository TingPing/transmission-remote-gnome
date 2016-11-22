# list_wrapper.py
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

from gi.repository import GObject, Gtk, Gio

class WrappedStore(Gtk.ListStore):
	"""Wraps a Gio.ListStore with a Gtk.ListStore"""

	@classmethod
	def new_for_model(cls, model, properties_map):
		"""
		properties_map: Ordered Dict of property names and types to map
		"""
		self = cls()
		self.set_column_types([v for k,v in properties_map.items()] + [GObject.Object])

		self._model = model
		self.properties = properties_map
		self._model.connect('items-changed', self._on_items_changed)
		self._on_items_changed(model, 0, 0, model.get_n_items())
		return self

	def _on_item_property_changed(self, item, property_name):
		# FIXME: Map property names...
		print('prop', property_name, 'changed')
		if property_name not in self.properties:
			return

		for row in self:
			if row[-1] == item:
				idx = self.properties.index(property_name)
				row[idx] = getattr(item.props, property_name)
				break

	def _on_items_changed(self, model, position, removed, added):
		if removed:
			# FIXME: Removes wrong value
			it = self[position].iter
			print('Removing', self[position][-1])
			while removed:
				item = model.get_item(position)
				item.disconnect(item._hook_id)
				item._hook_id = 0
				if not self.remove(it):
					print('Failed to remove list item')
				removed = removed - 1
		all_columns = [i for i in range(len(self.properties) + 1)]
		for i in range(added):
			new_pos = position + i
			item = model.get_item(new_pos)
			new_values = [getattr(item.props, prop) for prop in self.properties.keys()] + [item]
			self.insert_with_valuesv(new_pos, all_columns, new_values)
			hook_id = item.connect('notify', self._on_item_property_changed)
			item._hook_id = hook_id


		
