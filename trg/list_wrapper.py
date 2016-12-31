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
	def new_for_model(cls, model: Gio.ListModel, properties_map):
		"""
		properties_map: Ordered Dict of property names and types to map
		"""
		self = cls()

		self._property_types = list(properties_map.values()) + [GObject.Object]
		self.set_column_types(self._property_types)

		self._model = model
		self.properties = list(properties_map.keys())
		self._model.connect('items-changed', self._on_items_changed)
		self._on_items_changed(model, 0, 0, model.get_n_items())
		return self

	def _on_item_property_changed(self, item, paramspec):
		property_name = paramspec.name
		if property_name not in self.properties:
			return

		for row in self:
			if row[-1] == item:
				idx = self.properties.index(property_name)
				row[idx] = getattr(item.props, property_name)
				break

	@staticmethod
	def _fixup_value_types(values, types):
		"""
		Ensure the values are of the correct type, this is a problem when setting
		64bit types for example.
		"""
		fixed_values = []
		for i, value in enumerate(values):
			fixed_value = GObject.Value()
			fixed_value.init(types[i])
			fixed_value.set_value(value)
			fixed_values.append(fixed_value)
		return fixed_values

	def _on_items_changed(self, model, position, removed, added):
		while removed:
			row = self[position]
			item = row[-1]
			item.disconnect(item._hook_id)
			self.remove(row.iter)
			removed -= 1
		all_columns = [i for i in range(len(self.properties) + 1)]
		for i in range(added):
			new_pos = position + i
			item = model.get_item(new_pos)
			new_values = [getattr(item.props, prop) for prop in self.properties] + [item]
			new_values = self._fixup_value_types(new_values, self._property_types)
			self.insert_with_valuesv(new_pos, all_columns, new_values)
			hook_id = item.connect('notify', self._on_item_property_changed)
			item._hook_id = hook_id
