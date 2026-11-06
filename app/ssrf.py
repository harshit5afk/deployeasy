"""SSRF (Server-Side Request Forgery) protection and safe HTTP client for DeployEasy.

Prevents probes and webhook dispatch from accessing internal cloud metadata,
loopback interfaces, private networks (RFC 1918), link-local addresses,
and enforces safe redirect handling and webhook domain allowlists.
"""
import ipaddress
import socket
import urllib.parse
import urllib.request

DISCORD_ALLOWED_HOSTS = {"discord.com", "discordapp.com"}
SLACK_ALLOWED_HOSTS = {"hooks.slack.com"}

METADATA_HOSTNAMES = {
    "169.254.169.254",
    "metadata.google.internal",
    "instance-data",
    "100.100.100.200",  # Oracle cloud metadata
}


class SSRFValidationError(ValueError):
    """Raised when a target URL fails SSRF security constraints."""


def validate_ip_address(ip_obj: ipaddress.IPv4Address | ipaddress.IPv6Address) -> None:
    """Ensure an IP address is publicly routable and not in restricted ranges."""
    if (
        ip_obj.is_loopback
        or ip_obj.is_private
        or ip_obj.is_link_local
        or ip_obj.is_multicast
        or ip_obj.is_reserved
        or ip_obj.is_unspecified
    ):
        raise SSRFValidationError(f"Access to restricted IP address {ip_obj} is prohibited.")


def validate_target_url(url: str, allow_local_for_testing: bool = False) -> str:
    """Validate that target URL has a valid scheme and resolves only to non-internal addresses."""
    if not url or not isinstance(url, str):
        raise SSRFValidationError("URL must be a non-empty string.")

    parsed = urllib.parse.urlparse(url.strip())
    scheme = parsed.scheme.lower()
    if scheme not in ("http", "https"):
        raise SSRFValidationError(f"Invalid URL scheme '{scheme}'. Only HTTP and HTTPS are permitted.")

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        raise SSRFValidationError("URL must include a valid hostname.")

    if hostname in METADATA_HOSTNAMES:
        raise SSRFValidationError(f"Access to cloud metadata host '{hostname}' is prohibited.")

    if allow_local_for_testing:
        return url

    # Resolve all IP addresses for this hostname to prevent DNS rebinding
    port = parsed.port or (443 if scheme == "https" else 80)
    try:
        addr_info = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise SSRFValidationError(f"Could not resolve host '{hostname}': {exc}") from exc

    if not addr_info:
        raise SSRFValidationError(f"No IP addresses resolved for '{hostname}'.")

    for item in addr_info:
        sockaddr = item[4]
        ip_str = sockaddr[0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError as err:
            raise SSRFValidationError(f"Invalid IP address format: {ip_str}") from err

        validate_ip_address(ip_obj)

    return url


def validate_webhook_url(url: str, platform: str) -> str:
    """Validate that incoming webhook URL points exclusively to legitimate platform endpoints."""
    # First apply general SSRF validation
    parsed = urllib.parse.urlparse(url.strip())
    scheme = parsed.scheme.lower()
    if scheme != "https":
        raise SSRFValidationError("Webhook endpoints must use HTTPS.")

    hostname = (parsed.hostname or "").lower()
    path = parsed.path

    plat = platform.lower().strip()
    if plat == "discord":
        if hostname not in DISCORD_ALLOWED_HOSTS:
            raise SSRFValidationError(f"Invalid Discord webhook domain '{hostname}'. Allowed: discord.com, discordapp.com.")
        if not path.startswith("/api/webhooks/"):
            raise SSRFValidationError("Invalid Discord webhook path. Must begin with /api/webhooks/.")
    elif plat == "slack":
        if hostname not in SLACK_ALLOWED_HOSTS:
            raise SSRFValidationError(f"Invalid Slack webhook domain '{hostname}'. Allowed: hooks.slack.com.")
        if not path.startswith("/services/"):
            raise SSRFValidationError("Invalid Slack webhook path. Must begin with /services/.")

    # Validate resolved IPs as well
    return validate_target_url(url)


class SSRFSafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Custom HTTP redirect handler that validates redirect targets against SSRF rules."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Validate destination URL before following redirect
        try:
            validate_target_url(newurl)
        except SSRFValidationError as exc:
            raise SSRFValidationError(f"Redirect blocked by SSRF protection: {exc}") from exc
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def safe_urlopen(
    url: str,
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 5.0,
    allow_local_for_testing: bool = False,
):
    """Safely open an HTTP/HTTPS URL with SSRF checks on initial URL and all redirect hops."""
    validate_target_url(url, allow_local_for_testing=allow_local_for_testing)

    opener = urllib.request.build_opener(SSRFSafeRedirectHandler)
    req = urllib.request.Request(
        url,
        data=data,
        headers=headers or {"User-Agent": "DeployEasy-SafeClient/1.0"},
    )
    return opener.open(req, timeout=timeout)

