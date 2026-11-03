# 明度 1.2.0 · Preview 1

**一眼看亮度，顺手调到刚刚好。**

这次，明度更像 Mac 自带的一部分：点开菜单栏，拖动滑块，就能让每块屏幕亮得舒服。Windows 和 Ubuntu 也换上了更紧凑、统一的界面。

## 这次值得升级的地方

- **原生 Mac 面板。** 系统半透明材质、SF Symbols 图标和原生滑块，自动适配深浅色；点开即用，移开焦点即可收起。
- **亮度一眼可见。** 上方圆弧表示亮度，中间是加粗数值，底部太阳补齐圆形。可选择关注某块屏幕；显示设备确认的数值，多屏亮度不同时显示 `≠`。
- **Mac 安装更省心。** Apple Silicon 和 Intel 安装包均已内置所需亮度工具，无需 Homebrew，也不用首次启动再下载依赖。
- **多屏调节更顺手。** 每块屏幕独立滑块，夜间 25%、日常 60%、明亮 100% 一键切换；场景按钮调整所有屏幕。
- **安心驻留。** 启动只读取亮度，支持登录自启；调节失败会提示并恢复最近确认的数值。无需账号，本地运行，不上传屏幕信息。

## 选择你的安装包

| 系统 | 下载文件 |
|---|---|
| macOS 15+ · Apple Silicon | `mingdu-1.2.0-macos-arm64.dmg` |
| macOS 15+ · Intel | `mingdu-1.2.0-macos-x86_64.dmg` |
| Windows 10 / 11 · x64 | `mingdu-1.2.0-windows-x86_64-setup.exe` |
| Windows · 便携版 | `mingdu-1.2.0-windows-x86_64.zip` |
| Ubuntu 22.04 / 24.04 / 26.04 | `mingdu_1.2.0_all.deb` |
| Linux x86_64 · Qt 便携版 | `mingdu-1.2.0-linux-x86_64.tar.gz` |

**升级前先退出旧版明度。** Mac 打开 DMG 后替换“应用程序”中的 Mingdu.app；Windows 运行安装程序；Ubuntu 执行 `sudo apt install ./mingdu_1.2.0_all.deb`。个人设置保留，目前需手动更新。

详细步骤见附件 **INSTALL.md** 或[在线安装指南](https://github.com/ZhaoOyu/mingdu/blob/v1.2.0-preview.1/docs/INSTALL.md)。可用 **SHA256SUMS.txt** 检查下载完整性。

## 使用前了解

- 外接显示器需要支持并开启 **DDC/CI**。HDR、扩展坞、KVM 和部分转接方式可能影响调节。
- 这是预览版。Windows/macOS 安装包暂未进行受信任签名或 Apple 公证，首次打开可能出现系统提示，处理方式见安装指南。
- 发布流程要求 Windows、macOS 双架构和 Ubuntu 的自动测试及打包全部通过；自动测试使用模拟设备。Apple 背光屏幕与 Kuycon G27-X 已有本地亮度写入、读回及恢复验证，其他硬件兼容性仍需实际反馈。
- 当前界面为中文，专注亮度调节；唤醒、插拔屏幕或使用其他工具改变亮度后，请点击“刷新”。

遇到无法识别或调节的屏幕，先查看“设备诊断”，再[反馈系统、显示器型号和连接方式](https://github.com/ZhaoOyu/mingdu/issues/new/choose)。

---

**English:** A native macOS panel, a sun-shaped brightness ring, and a refreshed compact interface across platforms. Mac installers now bundle brightness helpers—no Homebrew required. Choose the package for your system above, quit the old app, and install the update. Settings are retained. See INSTALL.md for English instructions. This preview is unsigned/not notarized; external monitors need DDC/CI, and hardware compatibility varies. The current UI is Chinese; updates are manual.
