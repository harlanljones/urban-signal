"""HTTP for hosts whose responses break HTTP/1.1 header syntax.

httpx parses responses with h11, which rejects a header line with whitespace
between the field name and its colon ("illegal header line"). Jackson County,
OR's ArcGIS Server sends ``Content-Security-Policy : frame-ancestors ...`` on
every response (2026-09-30), so no httpx request to it completes.

The standard library's reader does not raise on that line, but it stops
reading headers there and loses every header after it, ``Content-Length``
among them. So requests to a listed host go through the standard library with
a reader that drops the whitespace before each field name's colon, and come
back as ordinary ``httpx.Response`` objects: callers keep their status checks,
JSON parsing and error handling. Proxies come from the environment, as httpx
takes them, and certificates are verified with httpx's own SSL context.
"""

import http.client
import re
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlparse

import httpx

TOLERANT_HEADER_HOSTS = frozenset(
    {
        # Jackson County, OR: Medford's deeds (Demog/PropertySales).
        "spatial.jacksoncountyor.gov",
    }
)

# A header line whose field name (RFC 9110 token characters) is followed by
# spaces or tabs before its colon.
_SPACE_BEFORE_COLON = re.compile(rb"^([!#$%&'*+\-.^_`|~0-9A-Za-z]+)[ \t]+:")

# Framing headers each side sets for itself: urllib from the request it sends,
# httpx from the content it is handed (already de-chunked).
_FRAMING_HEADERS = frozenset({"host", "connection", "content-length", "transfer-encoding", "keep-alive"})


class _HeaderLineFixer:
    """Wraps a response's socket file, fixing header lines while ``fixing``."""

    def __init__(self, fp: Any) -> None:
        self._fp = fp
        self.fixing = True

    def readline(self, limit: int = -1) -> bytes:
        line = self._fp.readline(limit)
        return _SPACE_BEFORE_COLON.sub(rb"\1:", line, count=1) if self.fixing else line

    def __getattr__(self, name: str) -> Any:
        return getattr(self._fp, name)


class _TolerantResponse(http.client.HTTPResponse):
    """Reads the status line and headers through the fixer, the body as sent."""

    def begin(self) -> None:
        fixer = _HeaderLineFixer(self.fp)
        self.fp = fixer
        try:
            super().begin()
        finally:
            fixer.fixing = False


class _TolerantHTTPConnection(http.client.HTTPConnection):
    response_class = _TolerantResponse


class _TolerantHTTPSConnection(http.client.HTTPSConnection):
    response_class = _TolerantResponse


class _TolerantHTTPHandler(urllib.request.HTTPHandler):
    def http_open(self, req: urllib.request.Request) -> Any:
        return self.do_open(_TolerantHTTPConnection, req)


class _TolerantHTTPSHandler(urllib.request.HTTPSHandler):
    def __init__(self, context: Any) -> None:
        super().__init__(context=context)
        self._tolerant_context = context

    def https_open(self, req: urllib.request.Request) -> Any:
        return self.do_open(_TolerantHTTPSConnection, req, context=self._tolerant_context)


class TolerantTransport(httpx.BaseTransport):
    """An httpx transport that sends each request through the standard library."""

    def __init__(self, timeout: float) -> None:
        self._timeout = timeout
        self._opener = urllib.request.build_opener(
            _TolerantHTTPHandler(), _TolerantHTTPSHandler(httpx.create_ssl_context())
        )

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        forwarded = urllib.request.Request(
            str(request.url),
            data=request.read() or None,
            headers={k: v for k, v in request.headers.items() if k.lower() not in _FRAMING_HEADERS},
            method=request.method,
        )
        try:
            response = self._opener.open(forwarded, timeout=self._timeout)
        except urllib.error.HTTPError as error:
            # A 4xx or 5xx answer is a response; the caller checks its status.
            response = error
        except (OSError, http.client.HTTPException) as error:
            raise httpx.TransportError(str(error), request=request) from error
        with response:
            try:
                content = response.read()
            except (OSError, http.client.HTTPException) as error:
                raise httpx.TransportError(str(error), request=request) from error
            headers = [(k, v) for k, v in response.headers.items() if k.lower() not in _FRAMING_HEADERS]
            status = response.status
        # A body sent with Content-Encoding stays encoded here; httpx decodes it.
        return httpx.Response(status, headers=headers, content=content, request=request)


def http_client(url: str, *, timeout: float) -> httpx.Client:
    """An httpx client for ``url``, through the standard library when its host is listed."""
    if urlparse(url).hostname in TOLERANT_HEADER_HOSTS:
        return httpx.Client(timeout=timeout, transport=TolerantTransport(timeout))
    return httpx.Client(timeout=timeout)


def get(url: str, *, params: dict[str, Any] | None = None, timeout: float = 5.0) -> httpx.Response:
    """``httpx.get`` for one request, through ``http_client``."""
    with http_client(url, timeout=timeout) as client:
        return client.get(url, params=params)
