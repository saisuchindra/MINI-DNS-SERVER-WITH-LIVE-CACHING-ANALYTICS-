"""Real upstream DNS client with a dnspython fallback."""
import asyncio
from dnslib import DNSRecord
import dns.asyncresolver
import dns.rdatatype

class UpstreamError(Exception): pass
class UpstreamResolver:
    def __init__(self, servers, port, timeout, retries): self.servers,self.port,self.timeout,self.retries=servers,port,timeout,retries
    async def resolve(self, request: DNSRecord, protocol="UDP") -> tuple[DNSRecord,str]:
        raw=request.pack(); errors=[]
        for server in self.servers:
            for _ in range(self.retries + 1):
                try:
                    data=await (self._tcp(raw,server) if protocol=="TCP" else self._udp(raw,server))
                    return DNSRecord.parse(data), server
                except Exception as e:
                    # asyncio.TimeoutError has an empty string representation; retain the type.
                    errors.append(f"{server}: {type(e).__name__}: {str(e) or 'no response'}")
        # Some hosted networks block direct DNS on port 53. Use dnspython's
        # system-configured resolver as a fallback so every supported record type works.
        try:
            return await self._dnspython_resolve(request, protocol), "dnspython"
        except Exception as e:
            errors.append(f"dnspython: {type(e).__name__}: {str(e) or 'no response'}")
        raise UpstreamError("All upstream resolvers failed: " + "; ".join(errors[-3:]))

    async def _dnspython_resolve(self, request: DNSRecord, protocol: str) -> DNSRecord:
        question = request.questions[0]
        resolver = dns.asyncresolver.Resolver()
        resolver.timeout = self.timeout
        resolver.lifetime = self.timeout * (self.retries + 1)
        answer = await resolver.resolve(
            str(question.qname),
            dns.rdatatype.to_text(question.qtype),
            tcp=protocol == "TCP",
            raise_on_no_answer=False,
        )
        response = DNSRecord.parse(answer.response.to_wire())
        response.header.id = request.header.id
        return response
    async def _udp(self, raw, server):
        loop=asyncio.get_running_loop(); sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); sock.setblocking(False)
        try:
            await loop.sock_sendto(sock,raw,(server,self.port)); data,_=await asyncio.wait_for(loop.sock_recvfrom(sock,65535),self.timeout); return data
        finally: sock.close()
    async def _tcp(self, raw, server):
        reader,writer=await asyncio.wait_for(asyncio.open_connection(server,self.port),self.timeout)
        try:
            writer.write(len(raw).to_bytes(2,'big')+raw); await writer.drain()
            size=int.from_bytes(await asyncio.wait_for(reader.readexactly(2),self.timeout),'big'); return await asyncio.wait_for(reader.readexactly(size),self.timeout)
        finally: writer.close(); await writer.wait_closed()
