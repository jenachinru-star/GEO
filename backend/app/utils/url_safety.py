import ipaddress
import re
from urllib.parse import urlparse

INTERNAL_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]

def is_safe_url(url: str) -> bool:
    """检查URL是否安全（不指向内网）"""
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    hostname = parsed.hostname
    if not hostname:
        return False
    if hostname.lower() in ("localhost", "localhost.localdomain"):
        return False
    # 检查是否是IP地址
    try:
        ip = ipaddress.ip_address(hostname)
        for network in INTERNAL_NETWORKS:
            if ip in network:
                return False
    except ValueError:
        # 是域名，暂时放行（生产环境可加DNS解析后再检查）
        pass
    return True
