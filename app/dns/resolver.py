"""Real upstream DNS client: sends original DNS wire packets over UDP or TCP."""
import asyncio, socket
from dnslib import DNSRecord, RR, A, AAAA, QTYPE

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
        # Some corporate, campus, and sandbox networks block direct DNS on port 53.
        # The OS resolver remains a genuine DNS lookup and uses the network's configured resolver.
        try:
            return await self._system_resolve(request), "system-resolver"
        except Exception as e:
            errors.append(f"system resolver: {type(e).__name__}: {str(e) or 'no response'}")
        raise UpstreamError("All upstream resolvers failed: " + "; ".join(errors[-3:]))

    async def _system_resolve(self, request: DNSRecord) -> DNSRecord:
        question = request.questions[0]
        record_type = QTYPE[question.qtype]
        if record_type not in {"A", "AAAA"}:
            raise UpstreamError(f"System resolver fallback supports A and AAAA, not {record_type}")
        family = socket.AF_INET if record_type == "A" else socket.AF_INET6
        addresses = await asyncio.get_running_loop().run_in_executor(
            None, lambda: socket.getaddrinfo(str(question.qname).rstrip("."), None, family, socket.SOCK_STREAM)
        )
        reply = request.reply()
        seen = set()
        for item in addresses:
            address = item[4][0]
            if address not in seen:
                seen.add(address)
                reply.add_answer(RR(question.qname, question.qtype, ttl=60, rdata=A(address) if record_type == "A" else AAAA(address)))
        if not seen:
            raise UpstreamError("System resolver returned no addresses")
        return reply
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
