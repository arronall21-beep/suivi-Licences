from fastapi import Request


def client_ip(request: Request) -> str:
    """Adresse IP du client (X-Forwarded-For si présent derrière le proxy nginx). Information indicative."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()[:64]
    return request.client.host if request.client else "inconnue"
