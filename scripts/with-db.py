#!/usr/bin/env python3
"""Run a command that needs this worktree's Postgres, from inside the sandbox.

    python3 scripts/with-db.py uv run pytest tests/test_uploader.py

The Bash sandbox gives each command its own network with only loopback, so
localhost:5433 has nothing behind it. Its only way out is the sandbox proxy,
which tunnels a TCP connection (HTTP CONNECT) to the hosts in
sandbox.network.allowedDomains, so "localhost:5433" has to be in that list.

This script listens on POSTGRES_HOST:POSTGRES_PORT inside the sandbox, sends
each connection through the proxy to the same address on the host, and runs
the command. Outside the sandbox (no proxy set, or the port is already taken
by the real Postgres) it just runs the command.

Only the network is narrowed here, to the Postgres server. Which database the
command reaches is up to the login in secrets/.env (role wt_<slug>, which can
only connect to its own clone).
"""

import base64
import os
import socket
import subprocess
import sys
import threading
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent


def setting(name: str, default: str) -> str:
    """Same lookup order as the backend: the env first, then secrets/.env."""
    if os.environ.get(name):
        return os.environ[name]
    env_file = ROOT / "secrets" / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            key, _, value = line.partition("=")
            if key.strip() == name and value.strip():
                return value.strip()
    return default


def proxy_url():
    for name in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"):
        if os.environ.get(name):
            return urlparse(os.environ[name])
    return None


def open_tunnel(proxy, target: str) -> tuple[socket.socket, bytes]:
    """CONNECT through the proxy; return the socket and any bytes past the reply."""
    upstream = socket.create_connection(
        (proxy.hostname, proxy.port or 3128), timeout=10
    )
    request = f"CONNECT {target} HTTP/1.1\r\nHost: {target}\r\n"
    if proxy.username:
        token = base64.b64encode(f"{proxy.username}:{proxy.password or ''}".encode())
        request += f"Proxy-Authorization: Basic {token.decode()}\r\n"
    upstream.sendall((request + "\r\n").encode())
    reply = b""
    while b"\r\n\r\n" not in reply:
        chunk = upstream.recv(4096)
        if not chunk:
            break
        reply += chunk
    head, _, rest = reply.partition(b"\r\n\r\n")
    status = head.split(b"\r\n", 1)[0].decode(errors="replace")
    if " 200 " not in f"{status} ":
        upstream.close()
        raise ConnectionError(
            f"the sandbox proxy refused {target} ({status}). "
            f'Is "{target}" in sandbox.network.allowedDomains?'
        )
    upstream.settimeout(None)
    return upstream, rest


def pump(src: socket.socket, dst: socket.socket) -> None:
    try:
        while data := src.recv(65536):
            dst.sendall(data)
    except OSError:
        pass
    finally:
        for sock, how in ((dst, socket.SHUT_WR), (src, socket.SHUT_RD)):
            try:
                sock.shutdown(how)
            except OSError:
                pass


def serve(client: socket.socket, proxy, target: str) -> None:
    try:
        upstream, rest = open_tunnel(proxy, target)
    except (OSError, ConnectionError) as e:
        print(f"with-db: {e}", file=sys.stderr)
        client.close()
        return
    if rest:
        client.sendall(rest)
    back = threading.Thread(target=pump, args=(upstream, client), daemon=True)
    back.start()
    pump(client, upstream)
    back.join()
    client.close()
    upstream.close()


def listen(host: str, port: int) -> list[socket.socket]:
    """Bind every address host resolves to (127.0.0.1 and ::1 for localhost)."""
    listeners = []
    for family, kind, proto, _, addr in socket.getaddrinfo(
        host, port, type=socket.SOCK_STREAM
    ):
        sock = socket.socket(family, kind, proto)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(addr)
        except OSError:
            sock.close()
            continue
        sock.listen(16)
        listeners.append(sock)
    return listeners


def accept_loop(listener: socket.socket, proxy, target: str) -> None:
    while True:
        client, _ = listener.accept()
        threading.Thread(
            target=serve, args=(client, proxy, target), daemon=True
        ).start()


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__.strip().splitlines()[2].strip(), file=sys.stderr)
        return 2
    command = sys.argv[1:]
    host = setting("POSTGRES_HOST", "localhost")
    port = int(setting("POSTGRES_PORT", "5432"))
    # SANDBOX_RUNTIME is set by the Claude Code sandbox. Outside it (a terminal,
    # CI, a corporate proxy) the command reaches Postgres directly.
    proxy = proxy_url() if os.environ.get("SANDBOX_RUNTIME") else None
    listeners = listen(host, port) if proxy else []
    for listener in listeners:
        threading.Thread(
            target=accept_loop, args=(listener, proxy, f"{host}:{port}"), daemon=True
        ).start()
    try:
        return subprocess.call(command)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
