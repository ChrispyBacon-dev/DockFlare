import re


def build_cloudflared_container_name(tunnel_name):
    if not tunnel_name:
        return None
    tunnel_name_str = str(tunnel_name).strip()
    if not tunnel_name_str:
        return None
    normalized = re.sub(r"[^a-zA-Z0-9_.-]+", "-", tunnel_name_str)
    normalized = re.sub(r"[-_.]{2,}", "-", normalized).strip("-_.")
    if not normalized:
        normalized = "tunnel"
    if not re.match(r"^[a-zA-Z0-9]", normalized):
        normalized = f"tunnel-{normalized}"
    max_suffix_len = 200
    normalized = normalized[:max_suffix_len].rstrip("-_.")
    if not normalized:
        normalized = "tunnel"
    return f"cloudflared-agent-{normalized}"
