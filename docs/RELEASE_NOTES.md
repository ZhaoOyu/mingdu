# 明度 1.1.0 · Preview 1

从状态栏调节每一块屏幕的亮度。本次预览提供 Ubuntu、macOS 和 Windows 安装包，无需自行搭建 Python 开发环境。

## 新功能

- 多显示器独立亮度滑块、托盘快捷操作、夜间／日常／明亮预设。
- Windows 系统托盘与 macOS 菜单栏界面，保留 Ubuntu GTK 轻量安装包。
- 内置屏幕背光与外接 DDC/CI 显示器适配，登录自启与单实例启动。
- 本地运行，无账户、无遥测。

## 选择下载

| 系统 | 文件 |
|---|---|
| Ubuntu 22.04 / 24.04 / 26.04 | `mingdu_1.1.0_all.deb` |
| macOS 15+ Apple Silicon | `mingdu-1.1.0-macos-arm64.dmg` |
| macOS 15+ Intel | `mingdu-1.1.0-macos-x86_64.dmg` |
| Windows 10 / 11 x64 | `mingdu-1.1.0-windows-x86_64-setup.exe` |
| Windows 便携版 | `mingdu-1.1.0-windows-x86_64.zip` |
| Linux x86_64 Qt 便携版 | `mingdu-1.1.0-linux-x86_64.tar.gz` |

Ubuntu：`sudo apt install ./mingdu_1.1.0_all.deb`。Windows：运行 setup.exe。macOS：拖入 Applications，并按需安装 Homebrew 辅助工具（brightness / m1ddc / ddcctl）。外接显示器须开启 DDC/CI。

完整步骤和英文说明见附件 **INSTALL.md** 或[在线安装指南](https://github.com/ZhaoOyu/mingdu/blob/v1.1.0-preview.1/docs/INSTALL.md)。附件 **SHA256SUMS.txt** 用于检查下载完整性。

## 预览版说明

- Ubuntu、Windows、macOS arm64/x86_64 自动测试及打包通过；测试使用模拟显示器，真实硬件兼容性尚待验证。
- Windows 安装程序经过静默安装、安装后启动和卸载测试；macOS 磁盘映像经过完整性验证。
- Windows/macOS 未做受信任代码签名或 Apple 公证，系统可能拦截首次运行。请参阅安装指南，不要关闭系统安全机制。
- 当前仅调节亮度，界面为中文；不含自动更新器。HDR、扩展坞、KVM 与部分连接方式可能不支持调节。

欢迎在 [Issues](https://github.com/ZhaoOyu/mingdu/issues/new/choose) 提交系统、显示器型号和连接方式，帮助完善兼容性。

---

**English:** First cross-platform preview with tray brightness controls, per-monitor sliders, presets and optional login startup. Download the package for your OS and architecture above. See INSTALL.md for English setup instructions. macOS needs hardware helper tools. Windows/macOS binaries are not trusted-signed/notarized. CI uses simulated devices; physical monitor support remains experimental. No automatic updater; current UI is Chinese.
