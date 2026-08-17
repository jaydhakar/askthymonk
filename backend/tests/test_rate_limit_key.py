"""Unit tests for the rate-limiter key function (main._client_ip_key).

slowapi buckets requests by whatever this function returns, so proving it returns
the forwarded real IP for distinct clients — and falls back to the socket IP when
the header is absent/malformed — is what proves per-IP bucketing. The full
end-to-end "two live clients get independent buckets" can only be proven once the
website proxy is deployed sending X-Real-Client-IP (pending, separate session).
"""

from starlette.requests import Request

from app import main


def _req(headers: dict[str, str], socket_ip: str = "10.0.0.1") -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/wisdom",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "client": (socket_ip, 12345),
    }
    return Request(scope)


def test_header_name_is_the_documented_contract():
    # Guards against an accidental rename diverging from what the website sends.
    assert main.CLIENT_IP_HEADER == "X-Real-Client-IP"


def test_uses_forwarded_ip_when_present():
    key = main._client_ip_key(_req({"X-Real-Client-IP": "203.0.113.7"}, socket_ip="10.0.0.1"))
    assert key == "203.0.113.7"  # forwarded IP wins over the socket IP


def test_distinct_forwarded_ips_bucket_separately():
    a = main._client_ip_key(_req({"X-Real-Client-IP": "203.0.113.7"}, socket_ip="10.0.0.1"))
    b = main._client_ip_key(_req({"X-Real-Client-IP": "198.51.100.2"}, socket_ip="10.0.0.1"))
    assert a != b  # same socket IP, different real IPs -> different buckets


def test_falls_back_to_socket_ip_when_header_absent():
    key = main._client_ip_key(_req({}, socket_ip="10.0.0.1"))
    assert key == "10.0.0.1"  # degrades to per-socket-IP, not a shared constant


def test_falls_back_to_socket_ip_when_header_malformed():
    key = main._client_ip_key(_req({"X-Real-Client-IP": "not-an-ip"}, socket_ip="10.0.0.1"))
    assert key == "10.0.0.1"


def test_empty_header_falls_back():
    key = main._client_ip_key(_req({"X-Real-Client-IP": "   "}, socket_ip="10.0.0.1"))
    assert key == "10.0.0.1"


def test_comma_list_takes_first_valid_entry():
    key = main._client_ip_key(_req({"X-Real-Client-IP": "203.0.113.7, 70.1.2.3"}, socket_ip="10.0.0.1"))
    assert key == "203.0.113.7"


def test_accepts_ipv6():
    key = main._client_ip_key(_req({"X-Real-Client-IP": "2001:db8::1"}, socket_ip="10.0.0.1"))
    assert key == "2001:db8::1"
