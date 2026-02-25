import time


class TTLCache:
    def __init__(self):
        self._store = {}

    def get(self, key):
        item = self._store.get(key)
        if not item:
            return None
        value, expires_at = item
        if expires_at < time.time():
            self._store.pop(key, None)
            return None
        return value

    def set(self, key, value, ttl_seconds: int):
        self._store[key] = (value, time.time() + ttl_seconds)

    def delete(self, key):
        self._store.pop(key, None)


cache = TTLCache()
