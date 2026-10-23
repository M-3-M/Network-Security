# netsec{UDP_bu7_w1th_f33l1ng5_e13063bc}

import asyncio
import hashlib
import ssl
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import override

from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.asyncio.server import serve
from aioquic.h3.connection import H3_ALPN, H3Connection
from aioquic.h3.events import DataReceived, H3Event, HeadersReceived
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import ProtocolNegotiated

BASE_DIR = Path(__file__).resolve().parent

cert_file = str(BASE_DIR / "server.cert")
key_file = str(BASE_DIR / "server.key")

PORT = 4433


# HTTP/3 UDP
class H3Protocol(QuicConnectionProtocol):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._http: H3Connection | None = None
        self._requests: dict[int, tuple[bytes, bytes, bytearray]] = {}

    @override
    def quic_event_received(self, event):
        if isinstance(event, ProtocolNegotiated):
            self._http = H3Connection(self._quic)
        if self._http is None:
            return
        for h3_event in self._http.handle_event(event):
            self._handle_h3_event(h3_event)

    def _handle_h3_event(self, event: H3Event) -> None:
        if isinstance(event, HeadersReceived):
            headers = dict(event.headers)
            method = headers.get(b":method", b"GET")
            path = headers.get(b":path", b"/").split(b"?")[0]
            self._requests[event.stream_id] = (method, path, bytearray())
            if event.stream_ended:
                self._respond(event.stream_id)
        elif isinstance(event, DataReceived):
            req = self._requests.get(event.stream_id)
            if req is not None:
                req[2].extend(event.data)
            if event.stream_ended:
                self._respond(event.stream_id)

    def _respond(self, stream_id: int) -> None:
        assert self._http is not None
        req = self._requests.pop(stream_id, None)
        if req is None:
            return
        method, path, data = req

        if method == b"POST" and path == b"/hash":
            body = hashlib.sha256(data).hexdigest().encode()
        elif path == b"/proto":
            body = b"HTTP/3"
        else:
            body = b""

        self._http.send_headers(
            stream_id=stream_id,
            headers=[
                (b":status", b"200"),
                (b"content-type", b"text/plain"),
                (b"content-length", str(len(body)).encode()),
            ],
        )
        self._http.send_data(stream_id=stream_id, data=body, end_stream=True)
        self.transmit()


# HTTPS TCP
class Handler(BaseHTTPRequestHandler):
    def _send(self, body: bytes) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Alt-Svc", f'h3=":{PORT}"')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        self._send(self.request_version.encode() if path == "/proto" else b"")

    def do_POST(self):
        path = self.path.split("?")[0]
        length = int(self.headers.get("Content-Length", 0))
        data = self.rfile.read(length)
        if path == "/hash":
            self._send(hashlib.sha256(data).hexdigest().encode())
        else:
            self._send(b"")


def run_https():
    httpd = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(cert_file, key_file)
    httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
    httpd.serve_forever()


async def main():
    threading.Thread(target=run_https, daemon=True).start()

    config = QuicConfiguration(is_client=False, alpn_protocols=H3_ALPN)
    config.load_cert_chain(cert_file, key_file)
    await serve("0.0.0.0", PORT, configuration=config, create_protocol=H3Protocol)
    await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
