SAFE ADB BRIDGE

Files:
  Start-SafeAdbBridge.cmd
  Start-SafeAdbBridge.ps1

Installation:
1. Copy both files into C:\platform-tools beside adb.exe.
2. Double-click Start-SafeAdbBridge.cmd.
3. Accept the SSH host key or enter the SSH password if prompted.
4. Keep the window open while using ADB from Ubuntu.

Ubuntu commands:
  hostadb devices
  hostadb adb -- shell getprop ro.product.model
  hostadb adb -- logcat

Security:
- Windows ADB listens only on 127.0.0.1:5037.
- Traffic is carried by an encrypted SSH reverse tunnel.
- No Windows firewall rule, administrator permission, scheduled task, or startup item is created.
- Closing the window removes the tunnel immediately.
