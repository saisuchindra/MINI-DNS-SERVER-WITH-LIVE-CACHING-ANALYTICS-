"""In-memory DNS response cache. TTL is evaluated on every lookup."""
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

@dataclass
class CacheEntry:
    domain: str; record_type: str; record_class: str; wire: bytes; answers: list[str]
    original_ttl: int; created_at: datetime; expires_at: datetime; last_accessed: datetime; hits: int = 0
    @property
    def ttl(self): return max(0, int((self.expires_at - datetime.now(timezone.utc)).total_seconds()))

class CacheManager:
    def __init__(self, max_entries=500):
        self.max_entries=max_entries; self._items=OrderedDict(); self.evictions=0; self.expired=0
    def _key(self, d,t,c="IN"): return (d.lower().rstrip("."),t.upper(),c.upper())
    def get(self, domain, record_type, record_class="IN") -> Optional[CacheEntry]:
        key=self._key(domain,record_type,record_class); entry=self._items.get(key)
        if not entry: return None
        if entry.ttl <= 0:
            del self._items[key]; self.expired += 1; return None
        entry.hits += 1; entry.last_accessed=datetime.now(timezone.utc); self._items.move_to_end(key); return entry
    def put(self, entry):
        key=self._key(entry.domain,entry.record_type,entry.record_class)
        if key not in self._items and len(self._items) >= self.max_entries:
            self._items.popitem(last=False); self.evictions += 1
        self._items[key]=entry; self._items.move_to_end(key)
    def clear(self): self._items.clear()
    def remove_domain(self, domain):
        keys=[k for k in self._items if k[0] == domain.lower().rstrip(".")]
        for key in keys: del self._items[key]
        return len(keys)
    def entries(self):
        self.purge(); return list(self._items.values())
    def purge(self):
        for k in list(self._items):
            if self._items[k].ttl <= 0: del self._items[k]; self.expired += 1
