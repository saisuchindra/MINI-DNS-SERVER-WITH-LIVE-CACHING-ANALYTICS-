import time, uuid, logging
from datetime import datetime, timezone, timedelta
from dnslib import DNSRecord, QTYPE
from app.cache.manager import CacheEntry
from app.dns.resolver import UpstreamError

SUPPORTED={"A","AAAA","CNAME","MX","NS"}
class DNSEngine:
    def __init__(self, cache,resolver,repository,events): self.cache,self.resolver,self.repo,self.events=cache,resolver,repository,events
    async def query(self, domain, record_type="A", protocol="UDP", simulation=False, request=None):
        domain=domain.lower().rstrip("."); record_type=record_type.upper(); flow=["Client Query Received", "DNS Packet Parsed", "Cache Lookup"]
        started=time.perf_counter(); cached=self.cache.get(domain,record_type)
        if cached:
            flow += ["Cache HIT", "Response Sent", "Analytics Updated"]
            result=self._result(domain,record_type,"HIT","cache",cached.answers,cached.ttl,protocol,started,flow,simulation,cached.wire)
        else:
            flow += ["Cache MISS", "Upstream DNS Query"]
            req=request or DNSRecord.question(domain,record_type)
            try:
                response,upstream=await self.resolver.resolve(req,protocol); answers=self._answers(response); ttl=min([int(r.ttl) for r in response.rr] or [0])
                wire=response.pack(); now=datetime.now(timezone.utc)
                if response.header.rcode == 0 and ttl > 0:
                    self.cache.put(CacheEntry(domain,record_type,"IN",wire,answers,ttl,now,now+timedelta(seconds=ttl),now)); flow.append("Cache Updated")
                flow += ["Response Received", "Response Sent", "Analytics Updated"]
                result=self._result(domain,record_type,"MISS","upstream",answers,ttl,protocol,started,flow,simulation,wire,upstream,"OK")
            except UpstreamError as e:
                flow += ["Upstream DNS Failed", "Analytics Updated"]
                result=self._result(domain,record_type,"MISS","upstream",[],0,protocol,started,flow,simulation,b"",None,"ERROR",str(e))
        self.repo.add_query(result); logging.info("QUERY domain=%s type=%s protocol=%s cache=%s source=%s latency=%.3fms",domain,record_type,protocol,result['status'],result['source'],result['response_time_ms']); await self.events.publish("dns_query",result); await self.events.publish("analytics_update",self.summary()); return result
    def _answers(self,response): return [str(r.rdata) for r in response.rr]
    def _result(self,d,t,status,source,ips,ttl,protocol,started,flow,simulation,wire,upstream=None,result_status="OK",error=None):
        return {"query_id":str(uuid.uuid4()),"timestamp":datetime.now(timezone.utc).isoformat(),"domain":d,"record_type":t,"status":status,"source":source,"ip_addresses":ips,"ttl":ttl,"protocol":protocol,"response_time_ms":round((time.perf_counter()-started)*1000,3),"flow":flow,"simulation_mode":simulation,"result_status":result_status,"error":error,"upstream":upstream,"wire":wire}
    def summary(self):
        rows=self.repo.all(); total=len(rows); hits=sum(r['cache_status']=='HIT' for r in rows); lat=[r['response_time_ms'] for r in rows]
        now=datetime.now(timezone.utc); recent=sum((now-datetime.fromisoformat(r['timestamp'])).total_seconds() < 60 for r in rows)
        return {"total_queries":total,"successful_queries":sum(r['status']=='OK' for r in rows),"failed_queries":sum(r['status']!='OK' for r in rows),"cache_hits":hits,"cache_misses":total-hits,"hit_ratio":round(100*hits/total,2) if total else 0,"miss_ratio":round(100*(total-hits)/total,2) if total else 0,"queries_per_second":round(recent/60,2),"cache_entries":len(self.cache.entries()),"cache_utilization":round(100*len(self.cache.entries())/self.cache.max_entries,2),"cache_evictions":self.cache.evictions,"expired_entries":self.cache.expired,"avg_latency_ms":round(sum(lat)/total,3) if total else 0,"min_latency_ms":min(lat,default=0),"max_latency_ms":max(lat,default=0),"udp_queries":sum(r['protocol']=='UDP' for r in rows),"tcp_queries":sum(r['protocol']=='TCP' for r in rows)}
