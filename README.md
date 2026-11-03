# 明度 · Mingdu

**一眼看亮度，顺手调到刚刚好。**

白天把外接屏调亮，入夜让笔记本柔和一点。明度把每块屏幕的亮度放进菜单栏：点开、拖动，就能找到舒服的光线，不必再摸索显示器背后的按钮。

免费、开源、本地运行，支持 **macOS、Windows 和 Ubuntu**。

[下载已发布预览版](#下载) · [安装指南](docs/INSTALL.md) · [反馈问题](https://github.com/ZhaoOyu/mingdu/issues) · [English](README.en.md)

> **1.2.0 Preview 1：原生 Mac 面板、太阳亮度圆环，全新上线。** Mac 所需辅助工具已随应用提供，无需安装 Homebrew；Windows 和 Ubuntu 也采用统一的紧凑布局。

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/preview-dark.png">
    <img src="docs/preview.png" width="366" alt="明度原生 Mac 面板：逐屏亮度滑块、夜间与日常预设、状态栏屏幕选择">
  </picture>
</p>
<p align="center"><sub>新版 Mac 控件预览，使用演示设备。系统半透明背景与阴影以实际运行为准。<a href="docs/preview-gtk.png">查看 Ubuntu 界面</a></sub></p>

<p align="center"><img src="docs/menubar.png" width="310" alt="亮度圆环：上方弧线、中间数值、底部太阳；示例为 0、25、78、100、多屏不同与错误状态"></p>

## 每天都用得上的小方便

- **像系统自带一样顺手。** Mac 原生菜单栏弹出面板，圆角、半透明材质与系统图标，随系统切换深浅色。点开即用，收起后安静驻留。
- **不用点开，也知道亮度。** 上方弧线表示亮度，中间显示数字，底部太阳补齐圆形。可以选择关注哪块屏幕；数值以设备确认结果为准。
- **每块屏幕，各有舒服的亮度。** 内置屏幕和外接显示器分别调节，也能一次调整全部屏幕。拖动原生滑块即可完成。
- **一键进入合适的光线。** 夜间 25%、日常 60%、明亮 100%，三个快捷按钮横向排列。环境变了，点一下就好。
- **Mac 装好就能开始。** 所需亮度工具随应用提供，无需安装 Homebrew，也无需首次启动再下载依赖。外接屏幕仍需支持并开启 DDC/CI。
- **打开时，尊重你原来的设置。** 启动只读取当前亮度；可选登录自启。调节失败时明确提示，并恢复显示最近一次确认的数值。
- **你的屏幕信息，留在本机。** 无需账号，不发送遥测，不上传显示器信息。

明度调节的是系统背光或显示器的硬件亮度，不靠黑色遮罩把画面盖暗。

## 下载

**当前版本：1.2.0 Preview 1。** 包含上方展示的新界面与太阳亮度圆环，欢迎体验并反馈显示器兼容性。

| 你的系统 | 下载 | 如何安装 |
|---|---|---|
| macOS 15+ · Apple Silicon | [arm64 DMG](https://github.com/ZhaoOyu/mingdu/releases/download/v1.2.0-preview.1/mingdu-1.2.0-macos-arm64.dmg) | 拖入“应用程序”，已内置辅助工具 |
| macOS 15+ · Intel | [Intel DMG](https://github.com/ZhaoOyu/mingdu/releases/download/v1.2.0-preview.1/mingdu-1.2.0-macos-x86_64.dmg) | 拖入“应用程序”，已内置辅助工具 |
| Windows 10 / 11 · x64 | [安装程序](https://github.com/ZhaoOyu/mingdu/releases/download/v1.2.0-preview.1/mingdu-1.2.0-windows-x86_64-setup.exe) | 双击安装，无需单独安装 Python |
| Ubuntu 22.04 / 24.04 / 26.04 | [DEB 安装包](https://github.com/ZhaoOyu/mingdu/releases/download/v1.2.0-preview.1/mingdu_1.2.0_all.deb) | 使用 apt 安装，自动处理系统依赖 |

[所有下载与校验文件](https://github.com/ZhaoOyu/mingdu/releases) · [完整安装步骤](docs/INSTALL.md)

Mac 与 Windows 预览包暂未完成受信任签名／Apple 公证，首次打开可能遇到系统提示，处理方式见安装指南。

## 三步，找到舒服的亮度

1. 打开明度，点击菜单栏或托盘图标。
2. 拖动对应屏幕的滑块，或者选择一个快捷场景。场景按钮会调整**所有屏幕**。
3. 在“状态栏屏幕”中选择最常关注的屏幕。插拔屏幕、唤醒电脑或用其他工具调光后，点击“刷新”。

希望每天自动就绪，可以勾选“登录系统时启动”。

### 圆环里的符号是什么意思？

| 显示 | 含义 |
|---|---|
| 数字 | 已确认的亮度百分比；图标省略百分号 |
| `≠` | 选择了“所有显示器”，但各屏亮度不同 |
| `!` | 所选范围内有屏幕调节失败，打开设备诊断查看原因 |
| `--` | 尚未读到可用的亮度数据 |

## 我的显示器能用吗？

内置屏幕需要系统支持背光调节；外接显示器需要支持 **DDC/CI**，通常可在显示器自身菜单中开启。部分 HDR 模式、扩展坞、KVM、转接器和 DisplayLink 连接会影响控制。

本机已对 Apple 背光屏幕与 Kuycon G27-X 做过亮度写入、读回和恢复检查。其他设备的兼容性仍需实际验证；原生 Mac 新界面另有模拟设备交互测试。详细范围见[验证记录](TESTING.md)。

明度目前专注**亮度**。遇到未识别或无法调节的屏幕，先展开“设备诊断”，再查看[常见问题](docs/INSTALL.md#常见问题)，或[提交兼容性反馈](https://github.com/ZhaoOyu/mingdu/issues/new/choose)。

## 一起让更多屏幕好用

欢迎分享你的系统、显示器型号和连接方式，也欢迎贡献代码、文档与翻译。

[贡献指南](CONTRIBUTING.md) · [更新记录](CHANGELOG.md) · [安全反馈](SECURITY.md)

明度采用 [MIT License](LICENSE)，第三方组件保留各自许可证，详见[第三方声明](THIRD_PARTY_NOTICES.md)。
