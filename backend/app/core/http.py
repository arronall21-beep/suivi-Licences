import ipaddress

from fastapi import Request

from app.core.config import settings


def client_ip(request: Request) -> str:
    """Adresse IP du client, utilisée pour la limitation des connexions et le journal d'audit.

    X-Forwarded-For est écrit par le client : seule la partie ajoutée par nos propres reverse proxies est fiable, c'est-à-dire
    les dernières entrées de la liste. `TRUSTED_PROXY_COUNT` (N) indique combien de proxies sont en place ; l'adresse du client
    est la N-ième entrée en partant de la droite, quoi que le client ait écrit à gauche. Sans proxy configuré (N = 0), ou si
    l'en-tête est absent, trop court ou invalide, on retombe sur l'adresse de la connexion : jamais sur une valeur non validée.
    """
    peer = request.client.host if request.client else "inconnue"
    hops = settings.trusted_proxy_count
    if hops <= 0:
        return peer
    entries = [e.strip() for e in request.headers.get("x-forwarded-for", "").split(",") if e.strip()]
    if len(entries) < hops:
        return peer
    try:
        address = ipaddress.ip_address(entries[-hops])
    except ValueError:
        return peer
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
        address = address.ipv4_mapped  # ::ffff:1.2.3.4 et 1.2.3.4 désignent le même client
    return str(address)
