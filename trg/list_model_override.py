from gi.repository import GObject, Gio


class ListModel:
	def __init__(self, store: Gio.ListModel):
		self._store = store
		self._type = store.get_item_type()

	def __getitem__(self, key: int):
		if not isinstance(key, int):
			raise TypeError()
		ret = self._store.get_item(key)
		if ret is None:
			raise IndexError()
		return ret

	def __len__(self) -> int:
		return self._store.get_n_items()

	def __iter__(self):
		for i in range(len(self)):
			yield self[i]


class ListStore(ListModel):
	"""Wrapper that implements a sequence"""
	def __setitem__(self, key: int, value: GObject.Object):
		if not isinstance(key, self._type):
			raise TypeError()
		if key >= len(self):
			raise IndexError()
		self._store.insert(key, value)

	def __delitem__(self, key: int):
		if not isinstance(key, int):
			raise TypeError()
		if key >= len(self):
			raise IndexError()
		self._store.remove(key)
