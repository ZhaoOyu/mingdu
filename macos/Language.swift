import Foundation

enum AppLanguage {
    static let choices = ["system", "zh-Hans", "en"]
    private static let testing = !Set(CommandLine.arguments).isDisjoint(with: ["--demo", "--ui-test", "--self-test"])
    private static var demoChoice = "system"
    static var choice: String {
        get {
            if testing { return demoChoice }
            let saved = UserDefaults.standard.string(forKey: "interfaceLanguage") ?? "system"
            return choices.contains(saved) ? saved : "system"
        }
        set {
            guard choices.contains(newValue) else { return }
            if testing { demoChoice = newValue }
            else { UserDefaults.standard.set(newValue, forKey: "interfaceLanguage") }
        }
    }
    static var english: Bool {
        let identifier = choice == "system" ? Locale.preferredLanguages.first ?? "en" : choice
        return !identifier.lowercased().hasPrefix("zh")
    }
    static var locale: Locale { Locale(identifier: english ? "en" : "zh-Hans") }
    static var names: [String] { [english ? "System default" : "跟随系统", "简体中文", "English"] }
}

// Fixed UI labels and fragments of hardware messages sent across process boundaries.
private let englishText: [String: String] = [
    "：": ": ",
    "，": ", ",
    "）": ")",
    "Apple 背光屏幕": "Apple display",
    "DDC/CI 写入失败。": "DDC/CI write failed.",
    "亮度": " brightness",
    "亮度已更新": "Brightness updated",
    "亮度需在 1–100 之间。": "Brightness must be between 1 and 100.",
    "内置显示器": "Built-in display",
    "刷新": "Refresh",
    "各屏幕亮度不同": "Displays have different brightness levels",
    "响应超时，请刷新。": "timed out. Click Refresh.",
    "外接显示器": "External display",
    "夜间": "Night",
    "屏幕已断开，请刷新。": "Display disconnected. Click Refresh.",
    "已读取当前亮度": "Current brightness loaded",
    "所有屏幕 · 快捷亮度": "Brightness presets for all displays",
    "所有显示器": "All displays",
    "无法建立明度会话。": "Could not start a Mingdu session.",
    "无法读取有效的 DDC/CI 亮度。": "Could not read DDC/CI brightness.",
    "日常": "Everyday",
    "明亮": "Bright",
    "明度": "Mingdu",
    "显示器已断开或标识不唯一，请刷新。": "Display disconnected or ambiguous. Click Refresh.",
    "未发现可调节屏幕": "No adjustable displays found",
    "正在应用亮度…": "Applying brightness…",
    "正在检测屏幕…": "Detecting displays…",
    "正在读取显示器…": "Reading displays…",
    "正在读取显示器亮度…": "Reading display brightness…",
    "演示": "Demo",
    "状态栏屏幕": "Menu bar display",
    "登录系统时启动": "Open at login",
    "设备诊断": "Diagnostics",
    "读取或写入失败，请检查连接及 DDC/CI。": "failed. Check the connection and DDC/CI.",
    "调节失败，请查看设备诊断": "Adjustment failed. Open display diagnostics.",
    "返回异常。": "returned an invalid response.",
    "连接或唤醒显示器后请刷新。外接屏幕需开启 DDC/CI。": "Refresh after connecting or waking a display. Enable DDC/CI on external monitors.",
    "连接显示器并开启 DDC/CI，然后点击刷新。": "Connect a display, enable DDC/CI and click Refresh.",
    "退出": "Quit",
]
private let fragments = try! NSRegularExpression(pattern: englishText.keys
    .sorted { $0.count > $1.count }.map(NSRegularExpression.escapedPattern(for:)).joined(separator: "|"))

func tr(_ text: String) -> String {
    guard AppLanguage.english else { return text }
    if let value = englishText[text] { return value }
    let source = text as NSString
    let matches = fragments.matches(in: text, range: NSRange(location: 0, length: source.length))
    guard !matches.isEmpty else { return text }
    let result = NSMutableString(string: text)
    for m in matches.reversed() {
        if let translated = englishText[source.substring(with: m.range)] {
            result.replaceCharacters(in: m.range, with: translated)
        }
    }
    return result as String
}
