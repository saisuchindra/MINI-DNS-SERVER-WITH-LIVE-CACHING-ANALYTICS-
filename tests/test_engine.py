import asyncio
from dnslib import DNSRecord, RR, A
from app.cache.manager import CacheManager
from app.database.repository import Repository
from app.dns.engine import DNSEngine
from app.events import EventHub
class Resolver:
    async def resolve(self,req,protocol):
        r=req.reply(); r.add_answer(RR(str(req.q.qname),rtype=1,ttl=30,rdata=A("1.2.3.4"))); return r,"test"
def test_miss_then_real_cache_hit(tmp_path):
    async def run():
        e=DNSEngine(CacheManager(),Resolver(),Repository(f"sqlite:///{tmp_path/'test.db'}"),EventHub())
        return await e.query("example.com"), await e.query("example.com")
    first, second=asyncio.run(run())
    assert first['status']=='MISS' and first['ip_addresses']==['1.2.3.4'] and second['status']=='HIT'
