# 明度 1.2.1 · Preview 1

Mac 用户现在可以打开菜单栏，用方向键把某块屏幕从 56% 微调到 55%。亮度条隐藏了密集刻度，每次调节仍精确到 1%。

- Swift 原生面板按当前屏幕的可用空间展开。橙色太阳表示亮度，蓝色和青色图标帮助区分内置与外接屏幕。
- 每块屏幕都可单独调节，也可以用 25%、60%、100% 三档预设调整全部屏幕。
- Mac 安装包自带对应芯片的亮度工具，拖入“应用程序”即可使用。

## 选择你的安装包

| 系统 | 下载文件 |
|---|---|
| macOS 15+ · Apple Silicon | `mingdu-1.2.1-macos-arm64.dmg` |
| macOS 15+ · Intel | `mingdu-1.2.1-macos-x86_64.dmg` |
| Windows 10 / 11 · x64 | `mingdu-1.2.1-windows-x86_64-setup.exe` |
| Windows · 便携版 | `mingdu-1.2.1-windows-x86_64.zip` |
| Ubuntu 22.04 / 24.04 / 26.04 | `mingdu_1.2.1_all.deb` |
| Linux x86_64 · Qt 便携版 | `mingdu-1.2.1-linux-x86_64.tar.gz` |

**升级前先退出旧版明度。** Mac 打开 DMG 后替换“应用程序”中的 Mingdu.app；Windows 运行安装程序；Ubuntu 执行 `sudo apt install ./mingdu_1.2.1_all.deb`。个人设置保留，目前需手动更新。

详细步骤见附件 **INSTALL.md** 或[在线安装指南](https://github.com/ZhaoOyu/mingdu/blob/v1.2.1-preview.1/docs/INSTALL.md)。可用 **SHA256SUMS.txt** 检查下载完整性。

## 使用前了解

- 外接显示器需要支持并开启 **DDC/CI**。HDR、扩展坞、KVM 和部分转接方式可能影响调节。
- 这是预览版。Windows/macOS 安装包暂未进行受信任签名或 Apple 公证，首次打开可能出现系统提示，处理方式见安装指南。
- 发布流程要求 Windows、macOS 双架构和 Ubuntu 的自动测试及打包全部通过；自动测试使用模拟设备。Apple 背光屏幕与 Kuycon G27-X 已有本地亮度写入、读回及恢复验证，其他硬件兼容性仍需实际反馈。
- 当前界面为中文，专注亮度调节；唤醒、插拔屏幕或使用其他工具改变亮度后，请点击“刷新”。

遇到无法识别或调节的屏幕，先查看“设备诊断”，再[反馈系统、显示器型号和连接方式](https://github.com/ZhaoOyu/mingdu/issues/new/choose)。

---

**English:** This preview brings a Swift menu bar panel to Mac. Focus the tick-free slider and use the arrow keys to adjust brightness by one percentage point. Both Mac installers include the required display helpers.
