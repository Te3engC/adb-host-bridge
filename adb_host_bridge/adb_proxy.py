from __future__ import annotations

import os
import re
import subprocess
import shutil
import sys
import time
from pathlib import Path

from .discovery import candidate_endpoints, discover


# Keep the client protocol pinned to the Windows bridge (1.0.41).  Using the
# system adb here made normal distro upgrades silently break the bridge.
PINNED_ADB_BINARY = (
    Path(__file__).resolve().parent.parent / "tools" / "adb-1.0.41" / "adb"
)


def resolve_adb_binary() -> str | None:
    """Resolve an explicit client first, otherwise use the pinned client."""
    explicit_binary = os.environ.get("HOSTADB_BINARY")
    if explicit_binary:
        return shutil.which(explicit_binary)
    if PINNED_ADB_BINARY.is_file():
        return str(PINNED_ADB_BINARY)
    return shutil.which("adb")


def discover_server():
    retries = max(1, int(os.environ.get("HOSTADB_DISCOVERY_RETRIES", "3")))
    retry_interval = float(os.environ.get("HOSTADB_DISCOVERY_INTERVAL", "0.2"))
    timeout = float(os.environ.get("HOSTADB_TIMEOUT", "0.7"))
    endpoints = candidate_endpoints()

    for attempt in range(retries):
        results = discover(endpoints, timeout)
        if results:
            return results
        if attempt + 1 < retries:
            time.sleep(retry_interval)
    return []


def main() -> int:
    adb = resolve_adb_binary()
    if not adb:
        print(
            "找不到本地 ADB 客户端。请安装 adb 或设置 HOSTADB_BINARY。",
            file=sys.stderr,
        )
        return 127

    results = discover_server()
    if not results:
        print(
            "未发现 ADB Server。请保持 Windows 的 Start-SafeAdbBridge.cmd 窗口运行。",
            file=sys.stderr,
        )
        return 1

    server_version = results[0].version
    version_check = subprocess.run(
        [adb, "version"],
        check=False,
        capture_output=True,
        text=True,
    )
    match = re.search(r"Android Debug Bridge version 1\.0\.(\d+)", version_check.stdout)
    if match and server_version.isdigit() and match.group(1) != server_version:
        print(
            f"ADB 版本不兼容：Windows Server={server_version}，"
            f"Ubuntu Client={match.group(1)}。请升级 Windows platform-tools 后重启安全桥。",
            file=sys.stderr,
        )
        return 3

    endpoint = results[0].endpoint
    env = os.environ.copy()
    env["ADB_SERVER_SOCKET"] = endpoint.socket_spec
    if os.environ.get("HOSTADB_VERBOSE"):
        print(
            f"hadb: {endpoint.host}:{endpoint.port} ({endpoint.source})",
            file=sys.stderr,
        )

    try:
        os.execvpe(adb, [adb, *sys.argv[1:]], env)
    except OSError as exc:
        print(f"无法启动 ADB 客户端：{exc}", file=sys.stderr)
        return 126


if __name__ == "__main__":
    raise SystemExit(main())
