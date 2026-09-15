from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys

from .discovery import DiscoveryResult, candidate_endpoints, discover, list_devices


def _add_discovery_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--host", action="append", default=[], help="优先探测 HOST 或 HOST:PORT，可重复")
    parser.add_argument("--port", type=int, default=5037, help="ADB Server 端口（默认 5037）")
    parser.add_argument("--timeout", type=float, default=0.7, help="单个地址的探测超时秒数")
    parser.add_argument("--scan", action="store_true", help="额外扫描本机/网关所在 /24 网段")


def _find(args: argparse.Namespace) -> list[DiscoveryResult]:
    endpoints = candidate_endpoints(args.host, args.port, args.scan)
    return discover(endpoints, args.timeout)


def _select(args: argparse.Namespace) -> DiscoveryResult | None:
    results = _find(args)
    return results[0] if results else None


def _print_not_found(scan: bool) -> None:
    suggestion = "" if scan else "；可添加 --scan 扫描局域网"
    print(
        "未发现可访问的 ADB Server。请确认宿主机使用 `adb -a -P 5037 nodaemon server` 启动，"
        f"且防火墙允许当前主机访问{suggestion}。",
        file=sys.stderr,
    )


def command_discover(args: argparse.Namespace) -> int:
    results = _find(args)
    if args.json:
        print(
            json.dumps(
                [
                    {
                        "host": item.endpoint.host,
                        "port": item.endpoint.port,
                        "source": item.endpoint.source,
                        "adb_server_version": item.version,
                    }
                    for item in results
                ],
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        for item in results:
            print(
                f"{item.endpoint.host}:{item.endpoint.port}\tADB server {item.version}\t"
                f"({item.endpoint.source})"
            )
    if not results:
        _print_not_found(args.scan)
        return 1
    return 0


def command_devices(args: argparse.Namespace) -> int:
    result = _select(args)
    if not result:
        _print_not_found(args.scan)
        return 1
    devices = list_devices(result.endpoint, max(args.timeout, 1.5))
    print(f"ADB Server: {result.endpoint.host}:{result.endpoint.port} ({result.endpoint.source})")
    print("List of devices attached")
    if devices:
        print(devices, end="" if devices.endswith("\n") else "\n")
    return 0


def command_env(args: argparse.Namespace) -> int:
    result = _select(args)
    if not result:
        _print_not_found(args.scan)
        return 1
    print(f"export ADB_SERVER_SOCKET={result.endpoint.socket_spec}")
    return 0


def command_adb(args: argparse.Namespace) -> int:
    result = _select(args)
    if not result:
        _print_not_found(args.scan)
        return 1
    adb = shutil.which(args.adb_binary)
    if not adb:
        print(f"找不到本地 ADB 客户端：{args.adb_binary}", file=sys.stderr)
        return 127
    adb_args = args.adb_args[1:] if args.adb_args[:1] == ["--"] else args.adb_args
    if not adb_args:
        adb_args = ["devices", "-l"]
    env = os.environ.copy()
    env["ADB_SERVER_SOCKET"] = result.endpoint.socket_spec
    print(f"使用 ADB Server {result.endpoint.host}:{result.endpoint.port}", file=sys.stderr)
    return subprocess.run([adb, *adb_args], env=env, check=False).returncode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hostadb", description="自动发现宿主机上的 ADB Server，并读取或复用它"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    discover_parser = subparsers.add_parser("discover", help="发现并验证所有 ADB Server")
    _add_discovery_options(discover_parser)
    discover_parser.add_argument("--json", action="store_true", help="输出 JSON")
    discover_parser.set_defaults(func=command_discover)

    devices_parser = subparsers.add_parser("devices", help="发现服务并直接列出设备（无需本地 adb）")
    _add_discovery_options(devices_parser)
    devices_parser.set_defaults(func=command_devices)

    env_parser = subparsers.add_parser("env", help="输出可供当前 shell 使用的环境变量")
    _add_discovery_options(env_parser)
    env_parser.set_defaults(func=command_env)

    adb_parser = subparsers.add_parser("adb", help="发现服务后调用本地 adb 客户端")
    _add_discovery_options(adb_parser)
    adb_parser.add_argument("--adb-binary", default="adb", help="本地 adb 客户端名称或路径")
    adb_parser.add_argument("adb_args", nargs=argparse.REMAINDER, help="传给 adb 的参数")
    adb_parser.set_defaults(func=command_adb)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (OSError, ValueError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 2
