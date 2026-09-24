import asyncio
from fastapi import WebSocket
class EventHub:
    def __init__(self): self.clients=set()
    async def connect(self, ws: WebSocket): await ws.accept(); self.clients.add(ws)
    def disconnect(self,ws): self.clients.discard(ws)
    async def publish(self,event,data):
        dead=[]
        for ws in self.clients:
            try: await ws.send_json({"event":event,"data":self.serializable(data)})
            except Exception: dead.append(ws)
        for ws in dead: self.disconnect(ws)
    def serializable(self,x):
        if isinstance(x,dict): return {k:self.serializable(v) for k,v in x.items() if k != 'wire'}
        if isinstance(x,list): return [self.serializable(v) for v in x]
        return x
