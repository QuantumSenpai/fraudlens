from ipaddress import ip_address, ip_network

from fastapi import HTTPException, Request

from services.config import settings


def resolve_client_ip(request: Request, override: str | None = None) -> str:
    if override:
        if settings.env.casefold() == "prod":
            raise HTTPException(status_code=403, detail="IP override is disabled in production")
        return str(ip_address(str(override)))

    remote = request.client.host if request.client else ""
    try:
        peer = ip_address(remote)
    except ValueError:
        return "0.0.0.0"
    for network in settings.trusted_proxy_ips.split(","):
        try:
            trusted = bool(network.strip()) and peer in ip_network(network.strip(), strict=False)
        except ValueError:
            continue
        if trusted:
            forwarded = request.headers.get("cf-connecting-ip") or request.headers.get("x-forwarded-for", "")
            candidate = forwarded.split(",", 1)[0].strip()
            try:
                return str(ip_address(candidate))
            except ValueError:
                break
    return str(peer)
