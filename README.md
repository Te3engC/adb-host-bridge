# ADB Host Bridge

`hostadb` 用于从 Linux、容器或 WSL 中自动发现宿主机运行的 ADB Server。它直接使用 ADB Server 协议验证目标，避免把“端口开放”误判成“ADB 可用”。

## 功能

- 自动尝试 `ADB_SERVER_SOCKET`、`ADB_HOST`、本机、默认网关、DNS/WSL 地址以及 Docker 宿主机别名。
- 可选扫描本机和默认网关所在的 `/24` 网段。
- 不依赖本地 `adb`，即可发现服务并执行 `host:devices-l`。
- 找到服务后，可自动设置 `ADB_SERVER_SOCKET` 并调用本地 `adb shell`、`adb logcat` 等命令。
- 仅使用 Python 标准库，无运行时第三方依赖。

## Windows 宿主机准备

在 Windows PowerShell 中运行：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\Enable-AdbHost.ps1 -AdbPath C:\platform-tools\adb.exe
```

脚本会以前台模式启动 ADB Server。保持窗口运行；结束时按 `Ctrl+C`。

> ADB Server 端口没有传输加密。Windows 防火墙应只允许可信私网或当前 Linux 主机访问 TCP 5037，切勿暴露到公网。

## 直接运行

项目无需安装：

```bash
cd /home/<user>/adb-host-bridge
python3 -m adb_host_bridge discover
python3 -m adb_host_bridge devices
```

默认候选找不到时，可扫描局域网：

```bash
python3 -m adb_host_bridge devices --scan
```

已知宿主机地址时可以优先指定：

```bash
python3 -m adb_host_bridge devices --host 192.168.1.10
```

输出供 shell 使用的变量：

```bash
eval "$(python3 -m adb_host_bridge env --scan)"
adb devices -l
```

自动发现后调用本地 ADB 客户端：

```bash
python3 -m adb_host_bridge adb --scan -- devices -l
python3 -m adb_host_bridge adb --scan -- shell getprop ro.product.model
python3 -m adb_host_bridge adb --scan -- logcat
```

## 安装为 `hostadb`

```bash
python3 -m pip install --user /home/<user>/adb-host-bridge
hostadb devices --scan
```

## 诊断

如果无法发现：

1. 确认 Windows 脚本窗口仍在运行。
2. 确认设备在 Windows 执行 `adb devices` 时状态为 `device`。
3. 确认 TCP 5037 未被防火墙拦截。
4. 使用 `hostadb devices --host <Windows-IP>` 区分自动发现问题与网络问题。

运行测试：

```bash
python3 -m unittest discover -s tests -v
```
