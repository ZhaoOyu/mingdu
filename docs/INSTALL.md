# 明度安装指南 / Installation

适用于 1.1.0 Preview 1。安装包来自 [GitHub Releases](https://github.com/ZhaoOyu/mingdu/releases/tag/v1.1.0-preview.1)，下载不需要登录 GitHub。预览版仍在收集真实显示器兼容性反馈。

## Ubuntu

推荐 Ubuntu 22.04 / 24.04 / 26.04 使用 `mingdu_1.1.0_all.deb`。在下载目录执行：

```sh
sudo apt update
sudo apt install ./mingdu_1.1.0_all.deb
mingdu
```

也可从应用菜单打开“明度”。deb 使用 GTK 界面，apt 自动安装 Python、GTK 与托盘依赖；不需要 pip 或自行配置 Python 环境。包不含原生架构二进制，但非 x86_64 设备尚未验证。

外接屏幕依赖 `ddcutil`，GNOME 状态栏依赖 AppIndicator 扩展，apt 默认推荐安装它们。如果禁用了推荐包，请手动安装：

```sh
sudo apt install ddcutil gnome-shell-extension-appindicator
```

启用 AppIndicator 扩展后，必要时注销并重新登录。显示器自身菜单中需开启 DDC/CI。若检测不到 I²C 总线，运行 `sudo modprobe i2c-dev`，再用 `ddcutil detect --brief` 和 `ddcutil environment` 检查。权限问题请按 [ddcutil 官方说明](https://www.ddcutil.com/i2c_permissions/) 配置，应用不会自动放宽设备权限，也不应使用 sudo 启动整个界面。

### Linux Qt 便携包

x86_64 系统可下载 `mingdu-1.1.0-linux-x86_64.tar.gz`，解压完整目录后运行 `Mingdu/Mingdu`。内置 Python 与 Qt，无需 pip；仍需系统桌面服务、外接屏幕的 ddcutil，以及 Qt 的系统运行库：

```sh
sudo apt install libegl1 libopengl0 libxcb-cursor0 libxkbcommon-x11-0 ddcutil
```

GNOME 仍需托盘扩展。建议优先使用 deb；不要同时启动 GTK 和 Qt 两个前端。

## macOS

1. 在“关于本机”查看芯片：Apple M 系列下载 `arm64.dmg`；Intel 下载 `x86_64.dmg`。预构建包要求 **macOS 15 或更高版本**。
2. 打开 DMG，将 `Mingdu.app` 拖到 `Applications`，然后弹出磁盘映像。
3. 安装需要的硬件辅助工具；应用已经包含 Python 与 Qt。
4. 从“应用程序”启动明度，在菜单栏图标中打开面板。

通过 [Homebrew](https://brew.sh/) 按需安装工具：

```sh
brew install brightness  # 内置屏幕及系统支持的 Apple 背光设备
brew install m1ddc       # Apple Silicon 外接 DDC/CI 显示器
# Intel Mac 外接显示器改用：brew install ddcctl
```

不必为了外接显示器安装 `brightness`，也不必同时安装 m1ddc 与 ddcctl。应用会查找 `/opt/homebrew/bin` 和 `/usr/local/bin`。Apple Silicon 使用原生 arm64 版本。工具已安装并不保证某个连接端口、转接器或显示器支持调节。

### 首次打开

预览包没有 Apple Developer ID 签名和公证，Gatekeeper 可能阻止打开。确认下载来自本项目且校验一致后，可依照 [Apple 官方的单个应用打开说明](https://support.apple.com/zh-cn/102445)操作；受管理电脑请遵守管理员要求。如果系统报告恶意软件或文件损坏，请停止运行并反馈。不要全局关闭 Gatekeeper。也可以按[贡献指南](../CONTRIBUTING.md)从源码运行。

## Windows

推荐 Windows 10 / 11 x64 使用 `mingdu-1.1.0-windows-x86_64-setup.exe`：

1. 双击安装程序，按向导安装。默认位置为 `%LOCALAPPDATA%\Programs\Mingdu`，无需管理员权限。
2. 从开始菜单打开 Mingdu；托盘图标可能位于折叠菜单中。
3. 点击图标调节亮度，需要时在应用里启用登录自启。

安装包内置 Python 与 Qt，无需额外安装。外接显示器通过 Windows 的 DDC/CI 接口调节；内置屏幕通过系统 PowerShell/WMI，需要显卡驱动支持。如果组织策略禁用了 PowerShell，内置屏幕控制可能不可用。

预览版尚无受信任的代码签名，SmartScreen 可能提示发布者未知。先确认来源与 SHA-256；不要关闭 Defender 或 SmartScreen。受组织策略阻止时请联系管理员，也可以从源码运行。

便携版 `mingdu-1.1.0-windows-x86_64.zip`：解压完整文件夹，运行 `Mingdu/Mingdu.exe`，不要单独复制 exe。启用登录自启前，把整个文件夹放在固定位置。

## 校验下载

从同一 Release 下载 `SHA256SUMS.txt`，与本地安装包计算结果比较。校验值用于发现损坏或与发布文件不一致，不能替代代码签名。

Ubuntu：

```sh
sha256sum mingdu_1.1.0_all.deb
```

macOS（Intel 请替换文件名）：

```sh
shasum -a 256 mingdu-1.1.0-macos-arm64.dmg
```

Windows PowerShell：

```powershell
Get-FileHash .\mingdu-1.1.0-windows-x86_64-setup.exe -Algorithm SHA256
```

## 更新与卸载

更新前从托盘退出明度；下载新版本后，Ubuntu 用 apt 安装，Windows 运行新安装程序，macOS 替换 Applications 中的应用。便携版整体替换目录。当前没有自动更新器。移动安装位置后，需要重新开启登录自启。

卸载前在应用内关闭登录自启并退出：

- Ubuntu deb：`sudo apt remove mingdu`。
- Windows 安装版：系统“设置 → 应用 → 已安装的应用”卸载 Mingdu。
- macOS：删除 Applications 中的 Mingdu.app。
- 便携版：删除解压目录。

个人设置默认保留在 Linux 的 `~/.config/mingdu`、Windows 的 `%APPDATA%\mingdu`、macOS 的 `~/Library/Application Support/mingdu`。

## 常见问题

**没有发现显示器？** 先开启显示器 OSD 菜单中的 DDC/CI，尽量用直连线材测试。HDR、扩展坞、KVM、USB 显示适配器和 DisplayLink 可能影响控制；内置 OLED 或虚拟机可能没有系统背光接口。macOS 需安装对应辅助工具。

**唤醒或插拔后不响应？** 点击刷新重新检测。当前不自动周期轮询。其他软件改变亮度后也需要刷新。

**状态栏没有图标？** Ubuntu GNOME 检查 AppIndicator 扩展，Windows 检查托盘折叠菜单。没有可用托盘时关闭面板会退出应用。

**需要提供诊断？** 使用安装后的可执行文件加 `--diagnose`。例如 Ubuntu `mingdu --diagnose`；macOS `/Applications/Mingdu.app/Contents/MacOS/Mingdu --diagnose`；Windows 在 PowerShell 中使用 `& "$env:LOCALAPPDATA\Programs\Mingdu\Mingdu.exe" --diagnose`（图形程序版本可能不显示控制台输出，可改用源码版）。诊断只读取设备，无设备时退出码为 1。提交反馈前删去序列号、设备标识与个人路径。请附系统、型号、连接方式与具体错误。

## English quick start

Download from the [preview release](https://github.com/ZhaoOyu/mingdu/releases/tag/v1.1.0-preview.1). The current application UI is Chinese. Physical monitor compatibility is still being tested.

- **Ubuntu 22.04 / 24.04 / 26.04:** run `sudo apt install ./mingdu_1.1.0_all.deb`, then launch `mingdu`. apt installs the GTK/Python dependencies; no pip needed. External monitors need `ddcutil`; GNOME needs its AppIndicator extension. Enable DDC/CI in the monitor menu. The Linux x86_64 Qt archive bundles Python/Qt but still needs the runtime libraries listed above.
- **macOS 15+:** choose arm64 for Apple Silicon or x86_64 for Intel. Open the DMG and drag Mingdu.app to Applications. Install helpers using Homebrew: `brew install brightness` for supported native backlights, `brew install m1ddc` for Apple Silicon external monitors, or `brew install ddcctl` for Intel external monitors. Python and Qt are bundled.
- **Windows 10/11 x64:** run the setup EXE. It installs per user without admin rights or a separate Python installation. Alternatively extract the complete portable ZIP and run Mingdu/Mingdu.exe. External monitors use Windows DDC/CI; internal brightness requires working PowerShell/WMI and driver support.

Windows/macOS previews do not have trusted signing or Apple notarization. Verify the release source and SHA-256; follow your OS's normal per-application review process and your organization's policies. Do not disable system protection. Apple's guidance: [opening an app from an unidentified developer](https://support.apple.com/en-us/102445).

Compare the installer hash with `SHA256SUMS.txt`, using `sha256sum` on Ubuntu, `shasum -a 256` on macOS, or `Get-FileHash -Algorithm SHA256` in PowerShell. SHA-256 checks integrity, not publisher identity.

Refresh after reconnecting or waking displays. Disable login startup and quit before uninstalling. Remove the deb with `sudo apt remove mingdu`, use Windows Installed Apps, or delete the macOS application/portable folder. Settings are retained. Updates are installed manually; there is no automatic updater.
