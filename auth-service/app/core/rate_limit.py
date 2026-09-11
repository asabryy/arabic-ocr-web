from fastapi import Request
from slowapi import Limiter

from app.core.config import settings


def get_client_ip(request: Request) -> str:
    """Real client IP behind ingress-nginx.

    `request.client.host` is the ingress pod's IP for every request, which would
    make all limits effectively global. ingress-nginx sets `X-Forwarded-For` to the
    connecting client's address (it overwrites, so it can't be spoofed in the
    current topology). The header name is configurable for other proxies.
    """
    header = request.headers.get(settings.CLIENT_IP_HEADER, "")
    if header:
        return header.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


limiter = Limiter(key_func=get_client_ip)
