import logging
from pathlib import Path
from contextlib import asynccontextmanager
from collections import Counter
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from app.config.settings import settings
from app.cache.manager import CacheManager
from app.database.repository import Repository
from app.dns.resolver import UpstreamResolver
from app.dns.engine import DNSEngine, SUPPORTED
from app.dns.server import DNSServer
from app.events import EventHub
from app.simulation import Simulation

Path("logs").mkdir(exist_ok=True)
logging.basicConfig(filename="logs/dns_server.log",level=getattr(logging,settings.log_level.upper()),format="%(asctime)s %(levelname)s %(message)s")
class Query(BaseModel):
    domain:str=Field(max_length=253); record_type:str="A"; protocol:str="UDP"
    @field_validator('domain')
    @classmethod
    def valid_domain(cls,v):
        labels=v.rstrip('.').split('.')
        if len(v)>253 or not v or any(not x or len(x)>63 or not x.replace('-','').isalnum() or x[0]=='-' or x[-1]=='-' for x in labels): raise ValueError('Invalid domain name')
        return v
    @field_validator('record_type')
    @classmethod
    def valid_type(cls,v):
        if v.upper() not in SUPPORTED: raise ValueError('Supported record types: '+', '.join(sorted(SUPPORTED)))
        return v.upper()
class SimConfig(BaseModel):
    interval_ms:int|None=Field(None,ge=20,le=60000); speed:str|None=None; real_dns:bool|None=None; record_type:str|None=None; maximum_queries:int|None=Field(None,ge=1,le=100000); domain_distribution:dict[str,float]|None=None
def envelope(data): return {"success":True,"data":data}
@asynccontextmanager
async def lifespan(app):
    cache=CacheManager(settings.cache_max_entries); repo=Repository(settings.database_url); hub=EventHub(); resolver=UpstreamResolver(settings.upstreams,settings.dns_upstream_port,settings.dns_timeout_seconds,settings.dns_retries); engine=DNSEngine(cache,resolver,repo,hub)
    app.state.engine=engine; app.state.cache=cache; app.state.repo=repo; app.state.hub=hub; app.state.simulation=Simulation(engine,hub,settings.simulation_interval_ms); app.state.dns=DNSServer(engine,settings.dns_host,settings.dns_port); app.state.dns_error=None
    try: await app.state.dns.start()
    except OSError as exc: app.state.dns_error=str(exc); logging.exception("DNS listener could not bind")
    yield; await app.state.simulation.stop(); await app.state.dns.stop()
app=FastAPI(title="Mini DNS Server with Live Caching Analytics",version="1.0.0",lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=settings.cors,allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
@app.get('/api/health')
async def health(): return envelope({"status":"healthy" if not app.state.dns_error else "degraded","dns_server":"running" if not app.state.dns_error else "unavailable","dns_error":app.state.dns_error,"cache":"running","database":"connected","simulation":app.state.simulation.state})
@app.post('/api/dns/query')
async def query(q:Query):
    result=await app.state.engine.query(q.domain,q.record_type,q.protocol)
    if result['result_status'] != 'OK': raise HTTPException(504,detail={"code":"DNS_TIMEOUT","message":result['error']})
    return envelope(app.state.hub.serializable(result))
@app.get('/api/dns/query/{query_id}')
async def get_query(query_id:str):
    item=app.state.repo.get_query(query_id)
    if not item: raise HTTPException(404,"Query not found")
    return envelope(item)
@app.get('/api/cache')
async def cache():
    return envelope([{"domain":e.domain,"record_type":e.record_type,"ttl":e.ttl,"original_ttl":e.original_ttl,"ip_addresses":e.answers,"hits":e.hits,"created_at":e.created_at.isoformat(),"expires_at":e.expires_at.isoformat(),"last_accessed":e.last_accessed.isoformat(),"status":"valid"} for e in app.state.cache.entries()])
@app.get('/api/cache/{domain}')
async def cache_domain(domain:str):
    entries=[e for e in app.state.cache.entries() if e.domain==domain.lower().rstrip('.')]
    if not entries: raise HTTPException(404,"Cache entry not found")
    return envelope([{"domain":e.domain,"record_type":e.record_type,"ttl":e.ttl,"hits":e.hits,"ip_addresses":e.answers} for e in entries])
@app.delete('/api/cache/{domain}')
async def clear_domain(domain:str): return envelope({"removed":app.state.cache.remove_domain(domain)})
@app.delete('/api/cache')
async def clear_cache(): app.state.cache.clear(); return envelope({"cleared":True})
@app.get('/api/analytics/summary')
async def summary(): return envelope(app.state.engine.summary())
@app.get('/api/analytics/domains')
async def domains():
    rows=app.state.repo.all(); counts=Counter(r['domain'] for r in rows); return envelope([{"domain":d,"query_count":n,"hit_count":sum(r['domain']==d and r['cache_status']=='HIT' for r in rows),"miss_count":sum(r['domain']==d and r['cache_status']=='MISS' for r in rows)} for d,n in counts.most_common(20)])
@app.get('/api/analytics/protocols')
async def protocols():
    rows=app.state.repo.all(); return envelope({"UDP":sum(r['protocol']=='UDP' for r in rows),"TCP":sum(r['protocol']=='TCP' for r in rows)})
@app.get('/api/analytics/cache')
async def analytics_cache():
    s=app.state.engine.summary(); return envelope({k:s[k] for k in ('cache_hits','cache_misses','hit_ratio','miss_ratio','cache_entries','cache_utilization','cache_evictions','expired_entries')})
@app.get('/api/analytics/timeseries')
async def timeseries(): return envelope(app.state.repo.recent(500))
@app.get('/api/logs')
async def logs(limit:int=50,offset:int=0): return envelope({"items":app.state.repo.recent(min(max(limit,1),500),max(offset,0)),"limit":limit,"offset":offset})
@app.post('/api/simulation/start')
async def sim_start(): return envelope(await app.state.simulation.start())
@app.post('/api/simulation/stop')
async def sim_stop(): return envelope(await app.state.simulation.stop())
@app.post('/api/simulation/pause')
async def sim_pause(): return envelope(await app.state.simulation.pause())
@app.post('/api/simulation/resume')
async def sim_resume(): return envelope(await app.state.simulation.resume())
@app.get('/api/simulation/status')
async def sim_status(): return envelope(app.state.simulation.status())
@app.post('/api/simulation/config')
async def sim_config(c:SimConfig): return envelope(await app.state.simulation.configure(c.model_dump()))
@app.websocket('/ws/analytics')
async def websocket(ws:WebSocket):
    await app.state.hub.connect(ws)
    try:
        await ws.send_json({"event":"analytics_update","data":app.state.engine.summary()})
        while True: await ws.receive_text()
    except WebSocketDisconnect: app.state.hub.disconnect(ws)
