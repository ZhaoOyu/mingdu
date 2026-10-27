# 明度 · Mingdu

**从状态栏，让每一块屏幕亮得刚刚好。**

明度是一款免费、开源的显示器亮度调节工具。在 Ubuntu 状态栏、macOS 菜单栏或 Windows 系统托盘中，随手调整内置屏幕和外接显示器的亮度，不必反复按显示器上的按钮。

[下载预览版](https://github.com/ZhaoOyu/mingdu/releases/tag/v1.1.0-preview.1) · [安装指南](docs/INSTALL.md) · [反馈问题](https://github.com/ZhaoOyu/mingdu/issues) · [English](README.en.md)

<p align="center"><img src="docs/preview.png" width="420" alt="明度亮度面板：两块屏幕的独立滑块、亮度预设和登录自启选项" /></p>
<p align="center"><sub>Qt 界面，使用模拟显示器演示。Ubuntu deb 使用原生 GTK 界面。</sub></p>

## 少一点操作，多一点舒适

- **多屏独立调节** — 为每块屏幕设置合适的亮度，也可以一起提高或降低。
- **状态栏随手可用** — 从托盘快捷调节，或打开面板拖动滑块；关闭面板后继续驻留。
- **一键切换场景** — 夜间、日常、明亮预设，适应不同环境。
- **调节真实背光** — 通过系统背光接口或 DDC/CI 改变硬件亮度，不叠加黑色遮罩。
- **按你的习惯启动** — 可开启登录自启；启动时读取当前亮度，不擅自覆盖显示器设置。
- **本地运行** — 无需账户，不发送遥测，不上传显示器信息。MIT 开源。

## 下载

**当前版本：1.1.0 Preview 1。** 适合愿意体验并反馈兼容性的用户。各平台已通过自动构建和模拟设备测试；真实显示器兼容性仍在收集，尚非稳定版。

| 系统 | 安装包 | 安装方式 |
|---|---|---|
| Ubuntu 22.04 / 24.04 / 26.04 | [下载 .deb](https://github.com/ZhaoOyu/mingdu/releases/download/v1.1.0-preview.1/mingdu_1.1.0_all.deb) | 使用 apt 安装，自动处理系统依赖 |
| macOS 15+ · Apple Silicon | [下载 arm64 .dmg](https://github.com/ZhaoOyu/mingdu/releases/download/v1.1.0-preview.1/mingdu-1.1.0-macos-arm64.dmg) | 拖入 Applications，按需安装辅助工具 |
| macOS 15+ · Intel | [下载 x86_64 .dmg](https://github.com/ZhaoOyu/mingdu/releases/download/v1.1.0-preview.1/mingdu-1.1.0-macos-x86_64.dmg) | 拖入 Applications，按需安装辅助工具 |
| Windows 10 / 11 · x64 | [下载安装程序](https://github.com/ZhaoOyu/mingdu/releases/download/v1.1.0-preview.1/mingdu-1.1.0-windows-x86_64-setup.exe) | 双击安装，无需单独安装 Python |

[发布页面](https://github.com/ZhaoOyu/mingdu/releases/tag/v1.1.0-preview.1)还提供 Windows 便携 ZIP、Linux Qt 压缩包和 SHA-256 校验文件。Windows 与 macOS 预览包尚未完成受信任代码签名／Apple 公证，首次打开可能被系统拦截，详见[安装指南](docs/INSTALL.md)。

### Ubuntu 快速开始

在下载目录打开终端：

```sh
sudo apt install ./mingdu_1.1.0_all.deb
mingdu
```

外接显示器请先在显示器自身菜单中开启 **DDC/CI**。其他平台的依赖及安装步骤见[完整安装指南](docs/INSTALL.md)。

## 日常使用

1. 从应用菜单启动明度，点击状态栏／托盘图标打开控制面板。
2. 拖动对应屏幕的滑块，或选择亮度预设。
3. 插拔显示器、电脑唤醒或用其他工具调节后，点击刷新。
4. 希望开机可用时，在应用中开启“登录自启”。

## 我的显示器能用吗？

内置屏幕需要系统提供可调背光接口，外接显示器需要支持并开启 DDC/CI。部分 HDR 模式、扩展坞、KVM、转接线和 DisplayLink 连接可能阻断亮度控制。macOS 还需要对应的辅助工具。

当前版本专注**亮度**，不提供对比度、音量或输入源切换。托盘滚轮支持取决于桌面环境，所有平台均可使用面板滑块。遇到未识别或无法调节的屏幕，请参考[排查步骤](docs/INSTALL.md#常见问题)，或[提交兼容性反馈](https://github.com/ZhaoOyu/mingdu/issues/new/choose)。

## 一起让更多屏幕好用

欢迎分享你的系统、显示器型号和连接方式，也欢迎贡献代码、文档与翻译。

[贡献指南](CONTRIBUTING.md) · [更新记录](CHANGELOG.md) · [测试范围](TESTING.md) · [安全反馈](SECURITY.md)

明度采用 [MIT License](LICENSE)，第三方组件遵循各自许可证，详见[第三方声明](THIRD_PARTY_NOTICES.md)。
