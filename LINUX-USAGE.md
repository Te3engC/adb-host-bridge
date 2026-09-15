# Linux 端使用说明

Windows 端先运行：

```text
C:\platform-tools\adb-host-bridge-windows-safe\Start-SafeAdbBridge.cmd
```

保持该窗口运行。新版安全桥使用加密 SSH 反向隧道：

```text
Ubuntu 127.0.0.1:15038 -> Windows 127.0.0.1:5037
```

## 检查连接

```bash
hadb devices -l
```

正常情况下会列出 Windows ADB 已识别的 Android 设备。

查看自动发现结果：

```bash
hostadb discover
```

直接使用协议读取设备列表，不调用本地 ADB 客户端：

```bash
hostadb devices
```

## 原生 ADB 兼容命令

`hadb` 会自动连接安全隧道，其余参数与原生 `adb` 相同：

```bash
hadb <adb 参数>
```

进入设备 Shell：

```bash
hadb shell
```

执行单条 Shell 命令：

```bash
hadb shell getprop ro.product.model
hadb shell uname -a
hadb shell ls -la /data/local/tmp
```

查看日志：

```bash
hadb logcat
hadb logcat -c
hadb logcat -s ActivityManager
```

安装和卸载应用：

```bash
hadb install app.apk
hadb install -r app.apk
hadb uninstall com.example.app
```

推送和拉取文件：

```bash
hadb push local-file.bin /data/local/tmp/
hadb pull /sdcard/Download/device-file.bin .
```

截图：

```bash
hadb exec-out screencap -p > screenshot.png
```

录屏：

```bash
hadb shell screenrecord /sdcard/demo.mp4
hadb pull /sdcard/demo.mp4 .
```

端口转发：

```bash
hadb forward tcp:8080 tcp:8080
hadb forward --list
hadb forward --remove tcp:8080
```

重启设备：

```bash
hadb reboot
hadb reboot bootloader
hadb reboot recovery
```

## 多设备选择

先查看序列号：

```bash
hadb devices -l
```

指定设备：

```bash
hadb -s SERIAL shell
hadb -s SERIAL logcat
hadb -s SERIAL install -r app.apk
```

## 环境变量

显示代理选择的 ADB Server：

```bash
HOSTADB_VERBOSE=1 hadb devices -l
```

修改探测超时：

```bash
HOSTADB_TIMEOUT=2 hadb devices -l
```

指定其他本地 ADB 客户端：

```bash
HOSTADB_BINARY=/path/to/adb hadb devices -l
```

指定其他安全隧道端口：

```bash
HOSTADB_TUNNEL_PORT=15038 hadb devices -l
```

## 故障排查

### 未发现 ADB Server

确认 Windows 安全桥窗口仍在运行，并显示：

```text
Ubuntu 127.0.0.1:15038 -> Windows 127.0.0.1:5037
```

Linux 检查监听端口：

```bash
ss -ltn 'sport = :15038'
```

### 设备列表为空

先在 Windows 检查：

```powershell
C:\platform-tools\adb.exe devices -l
```

如果 Windows 也没有设备，请检查 USB 连接、USB 调试开关和设备上的 RSA 授权提示。

### ADB 版本不兼容

Linux 桥接默认固定使用仓库内的协议 1.0.41 客户端，避免系统 ADB 升级
改变桥接行为。Windows 端也必须保持同一协议：

```text
Android Debug Bridge version 1.0.41
```

Windows 检查：

```powershell
C:\platform-tools\adb.exe version
```

Linux 检查：

```bash
/home/<user>/adb-host-bridge/tools/adb-1.0.41/adb version
```

### 服务管理

不要在 Linux 运行以下命令：

```bash
hadb kill-server
hadb start-server
```

Windows ADB Server 的生命周期由 `Start-SafeAdbBridge.cmd` 管理。需要重启时，关闭安全桥窗口并重新打开。
