# 明度 · Mingdu

[English](README.en.md) · [贡献指南](CONTRIBUTING.md) · [验证记录](TESTING.md)

从状态栏控制每一块屏幕。明度是一款 MIT 开源的显示器硬件亮度工具，提供多屏滑块、托盘快捷操作、亮度预设和登录自启。

<img src="docs/preview.png" width="420" alt="明度 Qt 演示模式面板，不代表真实硬件测试" />

**1.1 开发版：新增 Windows 与 macOS 后端及 Qt 跨平台界面。模拟测试不等于真实硬件兼容性认证，具体范围见 TESTING.md。**

## 平台与硬件

| 平台 | 界面 | 内置／原生背光 | 外接 DDC/CI | 状态 |
|---|---|---|---|---|
| Ubuntu 22.04 / 24.04 / 26.04 | Qt；小体积 deb 使用 GTK | sysfs + systemd-logind | ddcutil | 本地 GTK、Qt 模拟交互已测试；硬件待测 |
| Windows 10 / 11 x64 | Qt 系统托盘 | WMI（驱动支持时） | Windows DXVA2 | 实验性，适配与模拟测试已实现 |
| macOS Apple Silicon | Qt 菜单栏 | brightness 工具 | m1ddc | 实验性，需要对应辅助工具 |
| macOS Intel | Qt 菜单栏 | brightness 工具 | ddcctl | 实验性，需要对应辅助工具 |

Qt 源码版要求 Python 3.10+。macOS CI 构建目标为 macOS 15+，Intel 与 arm64 分开发行。更早的 macOS 可选择兼容的 Qt 版本自行测试，尚未验证。

## 功能

- 每块屏幕独立调节、全部提高／降低 5%，夜间／日常／明亮预设。
- 托盘菜单直接调节，连续滑块在独立面板中。滚轮仅在宿主转发事件时可用；Qt 不保证 Windows/macOS 托盘滚轮支持。
- 后台串行访问硬件，滑块防抖、待处理请求合并；失败恢复最近确认值。
- 启动只读取当前亮度，不覆盖硬件设置。无软件遮罩、无 gamma 调暗。
- 中文界面、演示模式、设备诊断、同一前端单实例和登录自启。
- 调节范围 1–100%，避免主动降至全黑；设备已有的 0% 仍如实显示。

当前仅开放亮度控制。对比度、音量和输入源是后续能力探测后的扩展，不会盲目写入。

## 安装与运行

### Ubuntu：deb / GTK

取得构建产物后：

```sh
sudo apt install ./mingdu_1.1.0_all.deb
mingdu
```

apt 安装 GTK、Python 和托盘依赖，默认推荐 ddcutil 与 Ubuntu AppIndicators 扩展。GNOME 需要启用扩展，新安装后可能需要注销登录。deb 不要求 pip。

源码目录也可运行 `./install.sh`，安装到 `~/.local/share/mingdu` 并添加应用菜单入口；需要先安装系统依赖：

```sh
sudo apt install python3-gi gir1.2-gtk-3.0 gir1.2-ayatanaappindicator3-0.1 libglib2.0-bin ddcutil gnome-shell-extension-appindicator
```

### Ubuntu / macOS：Qt 源码版

```sh
git clone https://github.com/ZhaoOyu/mingdu.git
cd mingdu
python3 -m venv .venv
.venv/bin/python -m pip install ".[qt]"
.venv/bin/python -m brightness --ui qt
```

Ubuntu 若缺少 venv，安装 `python3-venv`；外接屏幕安装 `ddcutil`。精简系统的 Qt 运行库可安装 `libegl1 libopengl0 libxcb-cursor0 libxkbcommon-x11-0`；GNOME 仍需托盘扩展。Wayland 与 X11 使用相同硬件后端。

macOS 辅助工具按需安装：

```sh
brew install brightness   # 内置屏幕及系统支持的 Apple 背光设备
brew install m1ddc       # Apple Silicon 外接 DDC/CI
# Intel Mac 使用：brew install ddcctl
```

Finder 启动时也会搜索 `/opt/homebrew/bin`、`/usr/local/bin`。Apple Silicon 请使用 arm64 Python/应用，不使用 Rosetta 的 x86_64 版本。HDMI、扩展坞、DisplayLink 的支持由硬件、macOS 和辅助工具决定。

### Windows：Qt 源码版

安装 Python 3.10+ 和 Git，在 PowerShell 运行：

```powershell
git clone https://github.com/ZhaoOyu/mingdu.git
cd mingdu
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install ".[qt]"
.venv\Scripts\python.exe -m brightness --ui qt
```

无需 ddcutil，不需要管理员权限。外接屏幕用系统 DXVA2，笔记本背光用系统 PowerShell/WMI。组策略限制 PowerShell、驱动不提供 WMI 接口时，内置调节可能不可用，其他设备仍可工作。

### 独立桌面包

[GitHub Actions](https://github.com/ZhaoOyu/mingdu/actions) 成功后上传各系统开发构建（需 GitHub 登录下载，保留 14 天）：

- Windows：解压完整 ZIP，启动 `Mingdu/Mingdu.exe`，不要只复制 exe。
- macOS：解压对应架构 ZIP，把 `Mingdu.app` 放入 Applications；仍需上述硬件工具。
- Linux：解压 tar.gz，运行 `Mingdu/Mingdu`；仍需 ddcutil/logind 与桌面服务。

当前构建未经 Windows 代码签名或 Apple Developer ID 签名／公证，可能被系统阻止。不要关闭系统安全机制；可从源码运行，或按组织的正常审批流程处理。目前没有生产稳定版承诺。

## 使用与诊断

从托盘菜单进入亮度控制。关闭面板后，有托盘时继续运行，无托盘时退出。登录自启请在最终安装路径启用，移动程序后需重新设置。

插拔、唤醒显示器，或用其他工具修改亮度后，点击刷新。当前不周期轮询。GTK 与 Qt 是两个可选前端，不应同时启动。

```sh
python -m brightness --demo --ui qt  # 模拟设备，不改变真实亮度
python -m brightness --diagnose     # 只读 JSON，无设备退出码为 1
python -m brightness --background
python -m brightness --ui gtk       # Ubuntu 系统 Python + GI
```

外接显示器请在实体 OSD 开启 **DDC/CI**。HDR、KVM、USB 显示适配器或线材可能阻断控制。不支持的设备不会伪装成可控设备。

Ubuntu 使用 `ddcutil detect --brief`、`ddcutil environment` 诊断。若 I²C 模块未加载，可运行 `sudo modprobe i2c-dev`。应用不会自动修改设备权限。内置屏幕需要 `/sys/class/backlight` 暴露设备，虚拟机和某些 OLED 通常没有此接口。

Windows 操作结束后释放物理显示器句柄；m1ddc 使用 UUID；ddcctl 每次写入前根据 UUID 重新解析序号。命令期间断开设备仍可能失败，请刷新后重试。

诊断可能包含设备标识或路径，提交 issue 前请删去序列号与个人路径。明度不发送遥测或上传显示器信息。

## 开发与构建

```sh
python -m pip install -e ".[qt,build]" ruff
python -m unittest discover -s tests -v
python tests/qt_smoke.py
python -m ruff check .
python -m build
python tools/build_desktop.py   # 必须在目标 OS / 架构执行
python tools/build_deb.py       # Ubuntu GTK 包，需要 dpkg-deb
```

GTK 测试：`xvfb-run -a dbus-run-session -- /usr/bin/python3 tests/ui_smoke.py`，需要系统 GTK、GI、Ayatana、Xvfb、xauth。Qt 测试使用 offscreen 渲染。

CI 覆盖 Ubuntu、Windows、macOS arm64/x64 模拟测试与原生构建，另有 GTK 回归任务。CI 成功只证明测试和打包完成，不证明某型号显示器必然兼容。

配置：Linux `~/.config/mingdu`；Windows `%APPDATA%\mingdu`；macOS `~/Library/Application Support/mingdu`。自启分别使用 XDG autostart、HKCU Run、LaunchAgent。

卸载前关闭登录自启。Ubuntu 用户安装用 `./install.sh --uninstall`，deb 用 `sudo apt remove mingdu`；独立桌面包删除解压目录／应用包。个人设置保留。

## 开源

[MIT License](LICENSE)。依赖保留各自许可证，见 [第三方声明](THIRD_PARTY_NOTICES.md)。欢迎按 [贡献指南](CONTRIBUTING.md) 提交代码与真实显示器兼容报告。
