"""Powtarzane zapytania DNS UDP z walidacją odpowiedzi i TCP fallback."""
import ipaddress, math, secrets, socket, statistics, struct, time
from .dns_profiles import PROFILES, benchmark_targets

class TruncatedResponse(ValueError): pass
PROVIDERS={p["name"]:p["ipv4"][0] for p in PROFILES.values()}

def question(name):
    encoded=name.rstrip(".").encode("idna"); labels=encoded.split(b".")
    if len(encoded)>253 or any(not x or len(x)>63 for x in labels): raise ValueError("Nieprawidłowa domena.")
    return b"".join(bytes([len(x)])+x for x in labels)+b"\0"+struct.pack("!HH",1,1)

def validate_response(packet,ident,query_bytes):
    if len(packet)<12+len(query_bytes): raise ValueError("Krótka odpowiedź DNS.")
    rid,flags,questions,answers,_,_=struct.unpack("!6H",packet[:12])
    if rid!=ident or not flags&0x8000 or flags&0x7800 or questions!=1 or packet[12:12+len(query_bytes)]!=query_bytes:
        raise ValueError("Odpowiedź nie pasuje do pytania.")
    if flags&0x200: raise TruncatedResponse("Odpowiedź ucięta.")
    if flags&15 or not answers: raise ValueError("Negatywna lub pusta odpowiedź DNS.")
    offset=12+len(query_bytes)
    for _ in range(answers):
        while True:
            if offset>=len(packet): raise ValueError("Brak nazwy rekordu.")
            length=packet[offset]; offset+=1
            if length==0: break
            if length&0xc0==0xc0:
                if offset>=len(packet): raise ValueError("Ucięty wskaźnik nazwy.")
                pointer=((length&0x3f)<<8)|packet[offset]; offset+=1
                if pointer>=len(packet): raise ValueError("Nieprawidłowy wskaźnik nazwy.")
                break
            if length>63 or offset+length>len(packet): raise ValueError("Ucięta nazwa.")
            offset+=length
        if offset+10>len(packet): raise ValueError("Ucięty rekord DNS.")
        rdlength=struct.unpack_from("!H",packet,offset+8)[0]; offset+=10
        if offset+rdlength>len(packet): raise ValueError("Ucięte dane rekordu.")
        offset+=rdlength

def receive_exact(sock,count,deadline):
    data=b""
    while len(data)<count:
        remaining=deadline-time.perf_counter()
        if remaining<=0: raise TimeoutError()
        sock.settimeout(remaining); chunk=sock.recv(count-len(data))
        if not chunk: raise ValueError("Przerwana odpowiedź TCP.")
        data+=chunk
    return data

def query(server,name,timeout=2,port=53):
    address=ipaddress.ip_address(server); ident=secrets.randbelow(65536); q=question(name)
    packet=struct.pack("!6H",ident,0x0100,1,0,0,0)+q; start=time.perf_counter()
    try:
        with socket.socket(socket.AF_INET6 if address.version==6 else socket.AF_INET,socket.SOCK_DGRAM) as sock:
            sock.settimeout(timeout); sock.connect((str(address),port)); sock.send(packet); response=sock.recv(4096)
        transport="UDP"
        try: validate_response(response,ident,q)
        except TruncatedResponse:
            transport="TCP_FALLBACK"; deadline=time.perf_counter()+timeout
            with socket.socket(socket.AF_INET6 if address.version==6 else socket.AF_INET,socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout); sock.connect((str(address),port)); sock.sendall(struct.pack("!H",len(packet))+packet)
                length=struct.unpack("!H",receive_exact(sock,2,deadline))[0]; response=receive_exact(sock,length,deadline)
            validate_response(response,ident,q)
        return {"ms":(time.perf_counter()-start)*1000,"status":"OK","transport":transport}
    except TimeoutError: return {"ms":None,"status":"TIMEOUT"}
    except (OSError,ValueError): return {"ms":None,"status":"ERROR"}

def summary(samples):
    if not samples: raise ValueError("Brak próbek.")
    values=sorted(x["ms"] for x in samples if x["status"]=="OK")
    return dict(count=len(samples),successful=len(values),min_ms=min(values) if values else None,
        max_ms=max(values) if values else None,mean_ms=statistics.mean(values) if values else None,
        median_ms=statistics.median(values) if values else None,
        p95_ms=values[math.ceil(.95*len(values))-1] if values else None,
        timeouts=sum(x["status"]=="TIMEOUT" for x in samples),
        error_rate=(len(samples)-len(values))/len(samples),
        tcp_fallbacks=sum(x.get("transport")=="TCP_FALLBACK" for x in samples),samples=samples)

def benchmark(servers=None,names=None,count=10,*,cancel_event=None):
    servers=list(servers or [x["address"] for x in benchmark_targets()])
    names=list(names or ["example.com","example.org","example.net"])
    if type(count) is not int or not 1 <= count <= 500: raise ValueError("Liczba prób musi być w zakresie 1–500.")
    if not 1 <= len(servers) <= 16 or not 1 <= len(names) <= 10: raise ValueError("Wymagane 1–16 resolverów i 1–10 nazw.")
    for server in servers: ipaddress.ip_address(server)
    for name in names: question(name)
    results={server:[] for server in servers}
    for i in range(count):
        for server in servers:
            if cancel_event is not None and cancel_event.is_set(): raise RuntimeError("Benchmark DNS przerwany.")
            results[server].append(query(server,names[i%len(names)]))
    rows={server:summary(samples) for server,samples in results.items()}
    ranking=sorted([{"server":server,**data} for server,data in rows.items()],
                   key=lambda x:(x["mean_ms"] is None,x["error_rate"],x["mean_ms"] if x["mean_ms"] is not None else float("inf")))
    return {"resolvers":rows,"ranking":ranking}
