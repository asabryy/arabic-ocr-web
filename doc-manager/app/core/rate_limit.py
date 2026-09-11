from fastapi import Request
from slowapi import Limiter

from app.core.config import settings


def get_client_ip(request: Request) -> str:
    """Real client IP behind ingress-nginx.

    `request.client.host` is the ingress pod for every request, which would make
    limits effectively global. ingress-nginx sets `X-Forwarded-For` to the connecting
    client (it overwrites the header, so it can't be spoofed in this topology). The
    header name is configurable for other proxies (e.g. CF-Connecting-IP).
    """
    header = request.headers.get(settings.CLIENT_IP_HEADER, "")
    if header:
        return header.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


limiter = Limiter(key_func=get_client_ip)
