"""In-memory 'database' array of inventory items."""


class InventoryStore:
    def __init__(self):
        self._items = []
        self._next_id = 1

    def all(self):
        return list(self._items)

    def get(self, item_id):
        return next((i for i in self._items if i["id"] == item_id), None)

    def find_by_barcode(self, barcode):
        if not barcode:
            return None
        return next((i for i in self._items if i.get("barcode") == barcode), None)

    def add(self, data):
        item = {"id": self._next_id, **data}
        self._next_id += 1
        self._items.append(item)
        return item

    def update(self, item_id, data):
        item = self.get(item_id)
        if item is not None:
            item.update(data)
        return item

    def delete(self, item_id):
        item = self.get(item_id)
        if item is not None:
            self._items.remove(item)
        return item
