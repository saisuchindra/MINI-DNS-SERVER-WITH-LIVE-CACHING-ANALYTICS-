"""DNS listeners. UDP carries a raw packet; TCP prefixes it with a two-byte length."""
import asyncio
from dnslib import DNSRecord, RCODE, QTYPE
class DNSProtocol(asyncio.DatagramProtocol):
    def __init__(self,engine): self.engine=engine
    def connection_made(self,t): self.transport=t
    def datagram_received(self,data,addr): asyncio.create_task(self.handle(data,addr))
    async def handle(self,data,addr):
        try:
            req=DNSRecord.parse(data); q=req.questions[0]; result=await self.engine.query(str(q.qname),QTYPE[q.qtype],"UDP",request=req)
            wire=result['wire'] or self.error(req,RCODE.SERVFAIL)
        except Exception: wire=self.error_from_raw(data)
        self.transport.sendto(wire,addr)
    def error(self,req,code):
        reply=req.reply(); reply.header.rcode=code; return reply.pack()
    def error_from_raw(self,data):
        try: return self.error(DNSRecord.parse(data),RCODE.FORMERR)
        except Exception: return b''
async def tcp_handler(reader,writer,engine):
    try:
        size=int.from_bytes(await reader.readexactly(2),'big'); req=DNSRecord.parse(await reader.readexactly(size)); q=req.questions[0]
        result=await engine.query(str(q.qname),QTYPE[q.qtype],"TCP",request=req); wire=result['wire']
        if not wire: reply=req.reply(); reply.header.rcode=RCODE.SERVFAIL; wire=reply.pack()
        writer.write(len(wire).to_bytes(2,'big')+wire); await writer.drain()
    except Exception: pass
    finally: writer.close(); await writer.wait_closed()
class DNSServer:
    def __init__(self,engine,host,port): self.engine,self.host,self.port=engine,host,port; self.transport=None; self.tcp=None
    async def start(self):
        loop=asyncio.get_running_loop(); self.transport,_=await loop.create_datagram_endpoint(lambda:DNSProtocol(self.engine),local_addr=(self.host,self.port)); self.tcp=await asyncio.start_server(lambda r,w:tcp_handler(r,w,self.engine),self.host,self.port)
    async def stop(self):
        if self.transport: self.transport.close()
        if self.tcp: self.tcp.close(); await self.tcp.wait_closed()
