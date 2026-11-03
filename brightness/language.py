"""Language choices for the desktop panels. A preference belongs to one app."""
import locale
import os
import re
import sys

CHOICES = ("system", "zh-Hans", "en")
choice = "system"


def system_language():
    if sys.platform == "darwin":
        from Foundation import NSLocale
        return str(NSLocale.preferredLanguages()[0])
    if sys.platform == "win32":
        import ctypes
        return locale.windows_locale.get(ctypes.windll.kernel32.GetUserDefaultUILanguage(), "en")
    return (os.environ.get("LANGUAGE") or os.environ.get("LC_ALL") or
            os.environ.get("LC_MESSAGES") or os.environ.get("LANG") or "en").split(":")[0]


def english():
    language = system_language() if choice == "system" else choice
    return not language.lower().startswith("zh")


def names():
    return ("System default" if english() else "跟随系统", "简体中文", "English")


def select(value):
    global choice
    choice = value if value in CHOICES else "system"


ENGLISH = {
    "Apple 屏幕已断开，无法确认设置结果": "Apple display disconnected. Could not confirm brightness.",
    "Apple 背光屏幕": "Apple display",
    "Apple 背光读取失败：": "Could not read Apple backlight: ",
    "Windows 内置背光不可用：": "Windows backlight unavailable: ",
    "Windows 显示器接口只能在 Windows 上运行": "This display interface requires Windows",
    "ddcctl 未能读取亮度，请检查 DDC/CI 和连接方式": "ddcctl could not read brightness. Check DDC/CI and the connection.",
    "ddcctl 返回了无效的亮度范围": "ddcctl returned an invalid brightness range",
    "m1ddc 返回了无法识别的亮度数据": "m1ddc returned an invalid brightness value",
    "macOS 外接屏幕检测失败：": "External display detection failed: ",
    "。": ".",
    "不是 Windows 可控制的设备": "This device cannot be controlled on Windows",
    "不是 macOS 可控制的设备": "This device cannot be controlled on macOS",
    "亮度": " brightness",
    "亮度已更新": "Brightness updated",
    "亮度必须在 1–100 之间": "Brightness must be between 1 and 100",
    "亮度百分比": " brightness percentage",
    "全部提高 5%": "Increase all by 5%",
    "全部降低 5%": "Decrease all by 5%",
    "内置屏幕": "Built-in display",
    "内置屏幕和 Apple 背光支持：请安装 brew install brightness。": "For Apple backlight support, install brightness with Homebrew.",
    "内置屏幕：需要系统提供 /sys/class/backlight 设备。": "Internal displays require a /sys/class/backlight device.",
    "刷新": "Refresh",
    "刷新显示器": "Refresh displays",
    "台屏幕": "displays",
    "台显示器": " displays",
    "台显示器亮度不同，请选择单块屏幕查看": " displays have different levels. Select one to view.",
    "启动命令不能包含换行": "Startup command cannot contain a newline",
    "启动器路径不能包含换行": "Launcher path cannot contain a newline",
    "命令执行失败": "Command failed",
    "响应超时，请检查显示器连接": "timed out. Check the display connection",
    "圆环": "Ring",
    "外接 DDC/CI 支持：请安装 brew install": "For external displays, run brew install",
    "外接屏幕": "External display",
    "外接屏幕支持未启用：请安装 ddcutil（sudo apt install ddcutil）。": "Install ddcutil to enable external displays (sudo apt install ddcutil).",
    "外接屏幕检测失败：": "External display detection failed: ",
    "外接屏幕：安装 ddcutil，在显示器菜单开启 DDC/CI。": "External monitors require ddcutil and DDC/CI.",
    "外接显示器": "External display",
    "夜间": "Night",
    "失败（Windows 错误": " failed (Windows error",
    "将所有显示器调节到": "Set all displays to",
    "已确认亮度": "confirmed brightness",
    "已读取当前亮度": "Current brightness loaded",
    "已读取当前亮度 · 拖动滑块即可调节": "Brightness loaded. Drag a slider to adjust.",
    "所有屏幕 · 快捷亮度": "Brightness presets for all displays",
    "所有显示器": "All displays",
    "打开亮度面板…": "Open brightness panel…",
    "找不到": "Could not find",
    "提高 5%": "Increase 5%",
    "提高亮度": "Increase brightness",
    "新版 Mac 安装包自带辅助工具。": "Mac downloads include the display tools.",
    "新版 macOS 安装包自带辅助工具；源码运行请参阅安装指南。": "Mac downloads include the display tools. See the installation guide for source builds.",
    "无法保存偏好设置：": "Could not save preferences: ",
    "无法保存设置：": "Could not save settings: ",
    "无法启动明度": "Could not start Mingdu",
    "无法更改自启动：": "Could not change startup: ",
    "无法确认 Windows 背光设置结果": "Could not confirm Windows backlight setting",
    "无法解析 Windows 背光信息": "Could not read Windows backlight information",
    "无法设置登录自启：": "Could not set login startup: ",
    "无法读取系统背光设备：": "Could not read the system backlight: ",
    "无法运行": "Could not run",
    "日常": "Everyday",
    "明亮": "Bright",
    "明度": "Mingdu",
    "明度 · 显示器亮度": "Mingdu · Display brightness",
    "明度可能正在启动，或实例锁不可访问。请稍后重试。": "Mingdu may be starting or the session lock is unavailable. Try again.",
    "明度：亮度调节失败": "Mingdu: brightness adjustment failed",
    "显示": "Show",
    "显示器已断开或标识不唯一，请刷新": "Display disconnected or ambiguous. Click Refresh",
    "显示器已断开或标识不唯一，请刷新设备": "Display disconnected or ambiguous. Rescan displays",
    "显示器未返回可调节的亮度（VCP 10），请开启 DDC/CI": "No brightness value (VCP 10). Enable DDC/CI.",
    "显示器返回了无效的亮度范围": "Invalid brightness range from display",
    "显示器返回的亮度范围无效": "Invalid brightness range from display",
    "显示器返回的最大亮度无效": "Invalid maximum brightness",
    "暂无可调节设备，请展开诊断查看原因。": "No adjustable displays. Open diagnostics for details.",
    "最大原始值": "maximum hardware value",
    "未发现可调节屏幕": "No adjustable displays found",
    "未发现可调节屏幕，请查看设备诊断。": "No adjustable displays. Open diagnostics.",
    "未发现可调节的显示器": "No adjustable displays",
    "未发现可调节的显示器。": "No adjustable displays found.",
    "未发现可调节设备，请展开设备诊断。": "No adjustable displays. Open diagnostics.",
    "未发现状态栏托盘宿主。GNOME 请安装并启用 Ubuntu AppIndicators 扩展；当前可继续使用窗口调节。": "No tray host found. Enable Ubuntu AppIndicators in GNOME, or use this window.",
    "未安装": "Not installed:",
    "未知的显示器类型：": "Unknown display type: ",
    "枚举桌面显示器": "Enumerate desktop displays",
    "枚举物理显示器": "Enumerate physical monitors",
    "检查连接并开启 DDC/CI，再点击刷新。": "Check the connection, enable DDC/CI and click Refresh.",
    "检测中": "Detecting…",
    "检测失败：": "Detection failed: ",
    "正在应用亮度…": "Applying brightness…",
    "正在检测显示器，DDC/CI 设备可能需要一些时间…": "Detecting displays. DDC/CI devices may take a moment…",
    "正在检测显示器，外接屏幕可能需要一些时间…": "Detecting displays. External monitors may take a moment…",
    "正在读取亮度": "Reading brightness",
    "正在读取显示器…": "Reading displays…",
    "正在读取显示器亮度…": "Reading display brightness…",
    "正在连接显示器…": "Connecting to displays…",
    "此平台暂不支持登录自启": "Login startup is unavailable on this platform",
    "此显示器无法读取 DDC/CI 亮度": "Could not read DDC/CI brightness on this display",
    "演示": "Demo",
    "演示模式：所有数值均为模拟，不会改变真实屏幕亮度。": "Demo mode uses simulated displays.",
    "演示设备": "Demo display",
    "然后点击右上角刷新。": "then click Refresh.",
    "状态栏屏幕": "Menu bar display",
    "状态栏显示与滚轮控制的屏幕": "Display used for the tray and scroll wheel",
    "状态栏显示的屏幕": "Display shown in the tray",
    "登录后自动启动": "Open at login",
    "登录系统时启动": "Open at login",
    "终端诊断：ddcutil detect；ddcutil environment。": "Terminal diagnostics: ddcutil detect and ddcutil environment.",
    "范围": "Range",
    "获取物理显示器句柄": "Get physical monitor handles",
    "设备检测失败：": "Display detection failed: ",
    "设备诊断": "Diagnostics",
    "设备诊断 ▸": "Diagnostics ▸",
    "设备诊断 ▾": "Diagnostics ▾",
    "设备读取失败：": "Could not read displays: ",
    "设置亮度": "Set brightness",
    "语言": "Language",
    "读取亮度": "Read brightness",
    "读取显示器信息": "Read display information",
    "调节失败，已恢复为最近一次确认的亮度；请查看设备诊断。": "Adjustment failed. Showing the last confirmed brightness. Open diagnostics.",
    "调节失败，已恢复显示最近确认值。请查看设备诊断。": "Adjustment failed. Showing the last confirmed brightness. Open diagnostics.",
    "调节失败，请查看设备诊断": "Adjustment failed. Open display diagnostics.",
    "调节失败：": " adjustment failed: ",
    "连接或唤醒显示器后请刷新。外接屏幕需开启 DDC/CI。": "Refresh after connecting or waking a display. Enable DDC/CI on external monitors.",
    "连接或唤醒显示器后请刷新。外接显示器需开启 DDC/CI。": "Refresh after connecting or waking a display. Enable DDC/CI on external monitors.",
    "连接或唤醒显示器后，请点击刷新重新检测。": "Click Refresh after connecting or waking a display.",
    "连接显示器并开启 DDC/CI，": "Connect a monitor and enable DDC/CI,",
    "连接显示器并开启 DDC/CI，再点击刷新。": "Connect a monitor, enable DDC/CI and click Refresh.",
    "退出": "Quit",
    "退出明度": "Quit Mingdu",
    "选择圆环显示和托盘滚轮控制的屏幕；滚轮支持取决于桌面环境。": "Choose the display for the ring and tray scrolling, where supported.",
    "部分显示器不支持 DDC/CI 或无法访问；请检查显示器菜单、连接线和 I²C 权限。": "Some monitors are inaccessible. Check DDC/CI, the connection and I²C permissions.",
    "部分显示器调节失败，请打开面板查看": "Some displays could not be adjusted. Open the panel.",
    "部分显示器调节失败，请查看设备诊断。": "Some displays could not be adjusted. Open diagnostics.",
    "部分设备调节失败，已回到最近确认值；请查看诊断。": "Some changes failed. Showing the last confirmed values. Open diagnostics.",
    "重新检测显示器": "Rescan displays",
    "重新检测显示器并读取当前亮度": "Rescan displays and read brightness",
    "降低 5%": "Decrease 5%",
    "降低亮度": "Decrease brightness",
    "首次安装依赖后可能需要注销并重新登录。": "You may need to sign out and back in after installation.",
    "驱动返回了异常的显示器数量": "Unexpected monitor count from the driver",
    "（": " (",
    "）": ")",
    "），请检查连接和 DDC/CI": "). Check the connection and DDC/CI",
    "，": ", ",
    "，请安装后刷新": ". Install it and click Refresh",
    "：": ": ",
    "；": "; "
}

_fragments = re.compile("|".join(re.escape(k) for k in sorted(ENGLISH, key=len, reverse=True)))


def tr(text):
    if not text or not english():
        return text
    if text in ENGLISH:
        return ENGLISH[text]
    return _fragments.sub(lambda m: ENGLISH[m.group()], text)
