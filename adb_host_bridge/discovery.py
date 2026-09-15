from __future__ import annotations

import ipaddress
import os
import socket
import struct
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


class AdbProtocolError(RuntimeError):
    pass


@dataclass(frozen=True)
class Endpoint:
    host: str
    port: int = 5037
    source: str = "unknown"

    @property
    def socket_spec(self) -> str:
        return f"tcp:{self.host}:{self.port}"


@dataclass(frozen=True)
class DiscoveryResult:
    endpoint: Endpoint
    version: str


def parse_endpoint(value: str, default_port: int = 5037, source: str = "argument") -> Endpoint:
    value = value.strip()
    if value.startswith("tcp:"):
        value = value[4:]
    if not value:
        raise ValueError("empty host")

    if value.startswith("["):
        closing = value.find("]")
        if closing < 0:
            raise ValueError(f"invalid IPv6 endpoint: {value}")
        host = value[1:closing]
        suffix = value[closing + 1 :]
        port = int(suffix[1:]) if suffix.startswith(":") else default_port
        return Endpoint(host, port, source)

    host, separator, possible_port = value.rpartition(":")
    if separator and host and possible_port.isdigit() and value.count(":") == 1:
        return Endpoint(host, int(possible_port), source)
    return Endpoint(value, default_port, source)


def _read_exact(sock: socket.socket, length: int) -> bytes:
    chunks: list[bytes] = []
    remaining = length
    while remaining:
        chunk = sock.recv(remaining)
        if not chunk:
            raise AdbProtocolError("ADB server closed the connection")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def adb_service(endpoint: Endpoint, service: str, timeout: float = 0.7) -> str:
    payload = service.encode("utf-8")
    request = f"{len(payload):04x}".encode("ascii") + payload
    with socket.create_connection((endpoint.host, endpoint.port), timeout=timeout) as sock:
        sock.settimeout(timeout)
        sock.sendall(request)
        status = _read_exact(sock, 4)
        if status == b"FAIL":
            message_length = int(_read_exact(sock, 4), 16)
            message = _read_exact(sock, message_length).decode("utf-8", "replace")
            raise AdbProtocolError(message)
        if status != b"OKAY":
            raise AdbProtocolError(f"unexpected ADB status: {status!r}")
        response_length = int(_read_exact(sock, 4), 16)
        return _read_exact(sock, response_length).decode("utf-8", "replace")


def probe(endpoint: Endpoint, timeout: float = 0.7) -> DiscoveryResult:
    version_hex = adb_service(endpoint, "host:version", timeout)
    try:
        version = str(int(version_hex, 16))
    except ValueError:
        version = version_hex
    return DiscoveryResult(endpoint, version)


def list_devices(endpoint: Endpoint, timeout: float = 1.5) -> str:
    return adb_service(endpoint, "host:devices-l", timeout)


def _default_gateway() -> str | None:
    route_file = Path("/proc/net/route")
    try:
        lines = route_file.read_text(encoding="ascii").splitlines()[1:]
    except OSError:
        return None
    for line in lines:
        fields = line.split()
        if len(fields) >= 4 and fields[1] == "00000000" and int(fields[3], 16) & 2:
            try:
                return socket.inet_ntoa(struct.pack("<L", int(fields[2], 16)))
            except (OSError, ValueError):
                continue
    return None


def _nameservers() -> Iterable[str]:
    try:
        lines = Path("/etc/resolv.conf").read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    return [line.split()[1] for line in lines if line.startswith("nameserver ") and len(line.split()) >= 2]


def candidate_endpoints(
    explicit: Iterable[str] = (), default_port: int = 5037, scan_subnet: bool = False
) -> list[Endpoint]:
    candidates: list[Endpoint] = []
    for value in explicit:
        candidates.append(parse_endpoint(value, default_port, "argument"))

    adb_socket = os.environ.get("ADB_SERVER_SOCKET")
    if adb_socket:
        try:
            candidates.append(parse_endpoint(adb_socket, default_port, "ADB_SERVER_SOCKET"))
        except ValueError:
            pass
    adb_host = os.environ.get("ADB_HOST")
    if adb_host:
        candidates.append(parse_endpoint(adb_host, default_port, "ADB_HOST"))

    ssh_connection = os.environ.get("SSH_CONNECTION", "").split()
    if ssh_connection:
        candidates.append(parse_endpoint(ssh_connection[0], default_port, "SSH client/host"))

    candidates.extend(
        [
            Endpoint(
                "127.0.0.1",
                int(os.environ.get("HOSTADB_TUNNEL_PORT", "15038")),
                "secure SSH reverse tunnel",
            ),
            Endpoint("127.0.0.1", 5038, "legacy SSH reverse tunnel"),
            Endpoint("127.0.0.1", default_port, "localhost"),
            Endpoint("host.docker.internal", default_port, "Docker host alias"),
            Endpoint("gateway.docker.internal", default_port, "Docker gateway alias"),
        ]
    )
    gateway = _default_gateway()
    if gateway:
        candidates.append(Endpoint(gateway, default_port, "default gateway"))
    candidates.extend(Endpoint(ns, default_port, "DNS/WSL host candidate") for ns in _nameservers())

    if scan_subnet:
        network_seeds: set[str] = set()
        if gateway:
            network_seeds.add(gateway)
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect(("192.0.2.1", 9))
                network_seeds.add(sock.getsockname()[0])
        except OSError:
            pass
        for seed in network_seeds:
            try:
                network = ipaddress.ip_network(f"{seed}/24", strict=False)
                candidates.extend(Endpoint(str(ip), default_port, "optional /24 scan") for ip in network.hosts())
            except ValueError:
                continue

    unique: list[Endpoint] = []
    seen: set[tuple[str, int]] = set()
    for candidate in candidates:
        key = (candidate.host, candidate.port)
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def discover(endpoints: Iterable[Endpoint], timeout: float = 0.7, workers: int = 32) -> list[DiscoveryResult]:
    endpoint_list = list(endpoints)
    if not endpoint_list:
        return []
    results: list[DiscoveryResult] = []
    with ThreadPoolExecutor(max_workers=min(workers, len(endpoint_list))) as executor:
        futures = {executor.submit(probe, endpoint, timeout): endpoint for endpoint in endpoint_list}
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except (OSError, ValueError, AdbProtocolError):
                pass
    return sorted(
        results,
        key=lambda item: (
            item.endpoint.source not in {"argument", "secure SSH reverse tunnel"}, item.endpoint.host
        ),
    )
