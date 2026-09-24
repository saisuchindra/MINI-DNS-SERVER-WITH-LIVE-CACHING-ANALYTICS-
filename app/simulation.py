import asyncio, random, uuid
from datetime import datetime, timezone
from dataclasses import dataclass, field

DEFAULT_DOMAINS={"google.com":25,"youtube.com":20,"github.com":15,"instagram.com":12,"amazon.com":10,"wikipedia.org":8,"openai.com":10}
class Simulation:
    def __init__(self, engine, events, interval=1000):
        self.engine,self.events=engine,events; self.config={"interval_ms":interval,"speed":"normal","real_dns":True,"record_type":"A","maximum_queries":None,"domain_distribution":DEFAULT_DOMAINS}; self.state="stopped"; self.count=0; self.task=None; self.run_id=None
    async def start(self):
        if self.state in ("running","paused"): return self.status()
        self.state="running"; self.count=0; self.run_id=str(uuid.uuid4()); self.engine.repo.start_simulation(self.run_id,datetime.now(timezone.utc).isoformat()); self.task=asyncio.create_task(self._run()); await self.events.publish("simulation_status",self.status()); return self.status()
    async def stop(self):
        self.state="stopped"
        if self.task: self.task.cancel(); self.task=None
        if self.run_id: self.engine.repo.finish_simulation(self.run_id,datetime.now(timezone.utc).isoformat(),"stopped",self.count)
        await self.events.publish("simulation_status",self.status()); return self.status()
    async def pause(self): self.state="paused"; await self.events.publish("simulation_status",self.status()); return self.status()
    async def resume(self):
        if self.state=="paused": self.state="running"
        await self.events.publish("simulation_status",self.status()); return self.status()
    async def configure(self, data):
        self.config.update({k:v for k,v in data.items() if v is not None}); return self.status()
    def status(self): return {"status":self.state,"query_count":self.count,"config":self.config}
    async def _run(self):
        try:
            while self.state != "stopped":
                if self.state == "running":
                    maxq=self.config.get("maximum_queries")
                    if maxq is not None and self.count >= maxq: self.state="stopped"; break
                    dist=self.config["domain_distribution"]; domain=random.choices(list(dist),weights=list(dist.values()),k=1)[0]
                    await self.engine.query(domain,self.config["record_type"],simulation=True); self.count += 1
                speed={"slow":2,"normal":1,"fast":0.25}.get(self.config["speed"],1)
                await asyncio.sleep(max(0.02,self.config["interval_ms"]*speed/1000))
        except asyncio.CancelledError: pass
        except Exception as exc: self.state="stopped"; await self.events.publish("error",{"message":str(exc)})
        finally:
            if self.run_id and self.state == "stopped": self.engine.repo.finish_simulation(self.run_id,datetime.now(timezone.utc).isoformat(),"stopped",self.count)
            await self.events.publish("simulation_status",self.status())
