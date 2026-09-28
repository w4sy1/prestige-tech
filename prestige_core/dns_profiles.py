"""Profile DNS dla Prestige DNS Center."""
from copy import deepcopy

PROFILES = {
    "cloudflare":{"name":"Cloudflare","short":"Cloudflare","category":"Prywatność / szybkość","description":"Publiczny resolver bez filtrowania treści.","ipv4":["1.1.1.1","1.0.0.1"],"ipv6":["2606:4700:4700::1111","2606:4700:4700::1001"],"doh":"https://cloudflare-dns.com/dns-query","dot":"one.one.one.one","filtering":"Brak"},
    "cloudflare-security":{"name":"Cloudflare Security","short":"Cloudflare Security","category":"Ochrona","description":"Cloudflare Families z blokowaniem malware i phishingu.","ipv4":["1.1.1.2","1.0.0.2"],"ipv6":["2606:4700:4700::1112","2606:4700:4700::1002"],"doh":"https://security.cloudflare-dns.com/dns-query","dot":"security.cloudflare-dns.com","filtering":"Malware / phishing"},
    "cloudflare-family":{"name":"Cloudflare Family","short":"Cloudflare Family","category":"Rodzina","description":"Cloudflare Families z filtrowaniem malware i treści dla dorosłych.","ipv4":["1.1.1.3","1.0.0.3"],"ipv6":["2606:4700:4700::1113","2606:4700:4700::1003"],"doh":"https://family.cloudflare-dns.com/dns-query","dot":"family.cloudflare-dns.com","filtering":"Malware + treści dla dorosłych"},
    "google":{"name":"Google Public DNS","short":"Google","category":"Uniwersalny","description":"Publiczny resolver Google.","ipv4":["8.8.8.8","8.8.4.4"],"ipv6":["2001:4860:4860::8888","2001:4860:4860::8844"],"doh":"https://dns.google/dns-query","dot":"dns.google","filtering":"Brak"},
    "quad9":{"name":"Quad9 Secure","short":"Quad9","category":"Ochrona","description":"Resolver prywatnościowy z blokowaniem znanych zagrożeń.","ipv4":["9.9.9.9","149.112.112.112"],"ipv6":["2620:fe::fe","2620:fe::9"],"doh":"https://dns.quad9.net/dns-query","dot":"dns.quad9.net","filtering":"Znane zagrożenia"},
    "adguard":{"name":"AdGuard DNS","short":"AdGuard","category":"Reklamy / tracking","description":"Publiczny AdGuard DNS blokujący reklamy i moduły śledzące.","ipv4":["94.140.14.14","94.140.15.15"],"ipv6":["2a10:50c0::ad1:ff","2a10:50c0::ad2:ff"],"doh":"https://dns.adguard-dns.com/dns-query","dot":"dns.adguard-dns.com","filtering":"Reklamy + tracking"},
    "adguard-family":{"name":"AdGuard Family","short":"AdGuard Family","category":"Rodzina","description":"AdGuard z filtrowaniem reklam, trackerów i treści dla dorosłych.","ipv4":["94.140.14.15","94.140.15.16"],"ipv6":["2a10:50c0::bad1:ff","2a10:50c0::bad2:ff"],"doh":"https://family.adguard-dns.com/dns-query","dot":"family.adguard-dns.com","filtering":"Reklamy + tracking + rodzina"},
    "adguard-unfiltered":{"name":"AdGuard Unfiltered","short":"AdGuard Unfiltered","category":"Bez filtrowania","description":"Infrastruktura AdGuard bez filtrowania zapytań.","ipv4":["94.140.14.140","94.140.14.141"],"ipv6":["2a10:50c0::1:ff","2a10:50c0::2:ff"],"doh":"https://unfiltered.adguard-dns.com/dns-query","dot":"unfiltered.adguard-dns.com","filtering":"Brak"},
}
ICONS={"cloudflare":"☁","cloudflare-security":"◆","cloudflare-family":"⌂","google":"G","quad9":"Q9","adguard":"A","adguard-family":"AF","adguard-unfiltered":"AU"}

def get_profile(key):
    if key not in PROFILES: raise KeyError(f"Nieznany profil DNS: {key}")
    return deepcopy(PROFILES[key])

def public_profiles(): return deepcopy(PROFILES)

def benchmark_targets():
    rows=[];seen=set()
    for key,p in PROFILES.items():
        address=p["ipv4"][0]
        if address in seen: continue
        seen.add(address); rows.append({"key":key,"name":p["name"],"address":address})
    return rows

def identify_provider(addresses):
    current={str(x).strip().lower() for x in (addresses or []) if str(x).strip()}
    if not current: return {"key":None,"name":"Brak danych","filtering":"Nieznane"}
    best=None
    for key,p in PROFILES.items():
        known={x.lower() for x in p["ipv4"]+p["ipv6"]}
        score=len(current & known)
        if score and (best is None or score>best[0]):
            best=(score,key,p)
    if best:
        return {"key":best[1],"name":best[2]["short"],"filtering":best[2]["filtering"]}
    return {"key":None,"name":"Niestandardowy / operator","filtering":"Nieznane"}
