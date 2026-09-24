from datetime import datetime, timezone, timedelta
from app.cache.manager import CacheManager, CacheEntry

def entry(domain="example.com",ttl=30):
    now=datetime.now(timezone.utc); return CacheEntry(domain,"A","IN",b"x",["1.2.3.4"],ttl,now,now+timedelta(seconds=ttl),now)
def test_hit_and_counter():
    c=CacheManager(); c.put(entry()); assert c.get("example.com","A").hits == 1
def test_expiration_is_miss():
    c=CacheManager(); c.put(entry(ttl=-1)); assert c.get("example.com","A") is None and c.expired == 1
def test_lru_eviction():
    c=CacheManager(1); c.put(entry("one.com")); c.put(entry("two.com")); assert c.get("one.com","A") is None and c.evictions == 1
