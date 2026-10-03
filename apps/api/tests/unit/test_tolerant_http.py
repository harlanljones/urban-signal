"""Requests to a host whose header lines break HTTP/1.1 syntax (2026-09-30).

Jackson County, OR's ArcGIS Server answers every request with
``Content-Security-Policy : frame-ancestors ...``, a space before the colon.
h11, under httpx, rejects the line; the standard library's reader stops at it
and loses the headers after it. A loopback server answers the same way here.
"""

import gzip
import json
import socketserver
import threading

import httpx
import pytest

from src.producers import tolerant_http
from src.producers.tolerant_http import TolerantTransport, http_client

_PROXY_VARIABLES = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy")


class _CountyHandler(socketserver.StreamRequestHandler):
    """Answers as the county's server does: the bad line comes before Date and
    Content-Length. ``/status/<code>`` answers with that status; a form POST
    is echoed back."""

    def handle(self):
        head = b""
        while not head.endswith(b"\r\n\r\n"):
            byte = self.rfile.read(1)
            if not byte:
                return
            head += byte
        lines = head.decode("latin-1").split("\r\n")
        path = lines[0].split(" ")[1]
        headers = {k.strip().lower(): v.strip() for k, _, v in (line.partition(":") for line in lines[1:] if line)}
        body = self.rfile.read(int(headers.get("content-length", 0)))
        status = int(path.split("/status/")[1].split("?")[0]) if "/status/" in path else 200
        payload = json.dumps({"path": path, "form": body.decode(), "pad": "x" * 2000}).encode()
        encoding = b""
        if "gzip" in headers.get("accept-encoding", ""):
            payload = gzip.compress(payload)
            encoding = b"Content-Encoding: gzip\r\n"
        self.wfile.write(
            f"HTTP/1.1 {status} Whatever\r\n".encode()
            + b"Content-Type: application/json;charset=UTF-8\r\n"
            + b"X-Powered-By: ASP.NET\r\n"
            + b"Content-Security-Policy : frame-ancestors *.jacksoncounty.org *.jacksoncountyor.gov;\r\n"
            + b"Date: Wed, 30 Sep 2026 17:56:42 GMT\r\n"
            + encoding
            + f"Content-Length: {len(payload)}\r\n\r\n".encode()
            + payload
        )


@pytest.fixture
def county(monkeypatch):
    for name in _PROXY_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("NO_PROXY", "127.0.0.1,localhost")
    server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), _CountyHandler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}/arcgis/rest/services/Demog/PropertySales/FeatureServer/0"
    server.shutdown()
    server.server_close()


def test_httpx_rejects_the_countys_header_line(county):
    with pytest.raises(httpx.RemoteProtocolError, match="illegal header line"):
        httpx.get(county, params={"f": "json"}, timeout=5)


def test_the_transport_reads_the_headers_after_the_bad_line_and_the_body(county):
    with httpx.Client(timeout=5, transport=TolerantTransport(5)) as client:
        response = client.get(county, params={"f": "json"})

    assert response.status_code == 200
    assert response.headers["content-security-policy"] == "frame-ancestors *.jacksoncounty.org *.jacksoncountyor.gov;"
    assert response.headers["date"] == "Wed, 30 Sep 2026 17:56:42 GMT"
    # httpx asks for gzip; the body arrives compressed and httpx decodes it.
    assert response.headers["content-encoding"] == "gzip"
    assert response.json()["path"].endswith("/FeatureServer/0?f=json")
    assert len(response.json()["pad"]) == 2000


def test_a_long_query_posts_its_form(county):
    with httpx.Client(timeout=5, transport=TolerantTransport(5)) as client:
        response = client.post(f"{county}/query", data={"where": "SiteCity = 'MEDFORD'", "f": "json"})

    assert response.json()["form"] == "where=SiteCity+%3D+%27MEDFORD%27&f=json"


def test_an_error_status_comes_back_as_a_response(county):
    with httpx.Client(timeout=5, transport=TolerantTransport(5)) as client:
        response = client.get(f"{county}/status/429")

    assert response.status_code == 429
    with pytest.raises(httpx.HTTPStatusError):
        response.raise_for_status()


@pytest.mark.usefixtures("county")
def test_a_refused_connection_is_a_transport_error():
    """The ArcGIS client retries a ``RequestError``, as it does for httpx's own."""
    with socketserver.TCPServer(("127.0.0.1", 0), _CountyHandler) as closed:
        dead = f"http://127.0.0.1:{closed.server_address[1]}/"
    with httpx.Client(timeout=5, transport=TolerantTransport(5)) as client, pytest.raises(httpx.TransportError):
        client.get(dead)


def test_only_a_listed_host_goes_through_the_transport(county, monkeypatch):
    with http_client(county, timeout=5) as client, pytest.raises(httpx.RemoteProtocolError):
        client.get(county)

    monkeypatch.setattr(tolerant_http, "TOLERANT_HEADER_HOSTS", frozenset({"127.0.0.1"}))
    assert tolerant_http.get(county, params={"f": "json"}).json()["path"].endswith("?f=json")


def test_the_county_host_is_listed():
    assert "spatial.jacksoncountyor.gov" in tolerant_http.TOLERANT_HEADER_HOSTS
