import AppKit
import CryptoKit
import SwiftUI

let args = CommandLine.arguments
let demo = args.contains("--demo")
let hardware = Hardware(demo: demo)
// Honour the same per-user lock, activation notification and preferences as existing installs.
let home = URL(fileURLWithPath: ProcessInfo.processInfo.environment["HOME"] ?? NSHomeDirectory())
let config = home.appendingPathComponent("Library/Application Support/mingdu")
let lockURL = config.appendingPathComponent(demo ? "native-demo.lock" : "native-main.lock")
let notificationName = Notification.Name("io.github.mingdu.activate." + SHA256.hash(data: Data(lockURL.path.utf8)).prefix(10).map { String(format:"%02x", $0) }.joined())
var instanceFD: Int32 = -1

final class BrightnessApp: NSObject, NSApplicationDelegate, ObservableObject {
    let panel = MenuPanel(), login = LoginItem(identifier: "io.github.mingdu.Brightness")
    let worker = DispatchQueue(label: "io.github.mingdu.hardware")
    @Published var devices = [DisplayDevice]()
    @Published var pending = [String: Int]()
    @Published var errors = Set<String>()
    @Published var warnings = [String]()
    @Published var busy = false
    @Published var diagnostics = false
    @Published var message = "正在读取显示器…"
    @Published var target = "all"
    var delayed = [String: DispatchWorkItem]()
    var revision = [String: Int]()
    var onScan: (() -> Void)?
    var selection: String { devices.contains(where: { $0.id == target }) ? target : "all" }
    func applicationDidFinishLaunching(_ notification: Notification) {
        let url = config.appendingPathComponent("settings.json")
        if !demo, let data = try? Data(contentsOf: url),
           let json = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any] { target = json["scroll_target"] as? String ?? "all" }
        panel.configure(BrightnessView(model: self))
        DistributedNotificationCenter.default().addObserver(self, selector: #selector(activate(_:)), name: notificationName, object: nil)
        let pid = String(getpid())
        _ = pid.withCString { write(instanceFD, $0, strlen($0)) }
        if args.contains("--smoke-test") {
            onScan = {
                precondition(self.devices.count == 2 && self.reading == "≠")
                self.setLanguage("en")
                precondition(self.panel.item.button?.toolTip?.hasPrefix("Mingdu") == true)
                self.setLanguage("zh-Hans")
                precondition(self.panel.item.button?.toolTip?.hasPrefix("明度") == true)
                self.setLanguage("system")
                self.setTarget(self.devices[0].id)
                precondition(self.reading == "60")
                self.request(self.devices[0], 25)
                DispatchQueue.main.asyncAfter(deadline: .now()+0.5) { self.panel.item.button?.performClick(nil) }
                DispatchQueue.main.asyncAfter(deadline: .now()+1.3) {
                    precondition(self.reading == "25" && self.pending.isEmpty)
                    self.panel.verifyVisibleContent()
                    NSApp.terminate(nil)
                }
            }
        }
        scan()
        if !args.contains("--background") && !args.contains("--smoke-test") { panel.show() }
    }
    @objc func activate(_ note: Notification) { panel.show() }
    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool { panel.show(); return true }
    func applicationWillTerminate(_ notification: Notification) {
        ftruncate(instanceFD, 0)
        close(instanceFD)
    }
    func setTarget(_ key: String) {
        target = key
        if !demo {
            do { try JSONEncoder().encode(["scroll_target": key]).write(to: config.appendingPathComponent("settings.json"), options: .atomic) }
            catch { message = error.localizedDescription }
        }
        updateIcon()
    }
    var reading: String {
        let selected = devices.filter { selection == "all" || $0.id == target }
        if selected.contains(where: { errors.contains($0.id) }) { return "!" }
        let values = Set(selected.map(\.value))
        return values.count > 1 ? "≠" : values.first.map(String.init) ?? "--"
    }
    func updateIcon() {
        let text = reading
        panel.item.button?.image = ringImage(number: text, fraction: Double(text).map { $0/100 }, marker: "sun")
        panel.item.button?.title = demo ? tr(" 演示") : ""
        panel.item.button?.toolTip = tr("明度 · ") + (Int(text) != nil ? text+"%" : text == "≠" ? tr("各屏幕亮度不同") : tr(message))
        panel.item.button?.setAccessibilityLabel(panel.item.button?.toolTip)
    }
    func scan() {
        guard !busy, pending.isEmpty else { return }
        busy = true
        message = "正在读取显示器亮度…"
        worker.async {
            let result = hardware.scan()
            DispatchQueue.main.async {
                if !demo || self.devices.isEmpty { self.devices = result.displays }
                self.warnings = result.warnings
                self.errors.removeAll()
                self.busy = false
                self.diagnostics = self.devices.isEmpty
                self.message = self.devices.isEmpty ? "未发现可调节屏幕" : "已读取当前亮度"
                self.updateIcon()
                self.onScan?()
                self.onScan = nil
            }
        }
    }
    func request(_ device: DisplayDevice, _ value: Int) {
        guard !busy else { return }
        let key = device.id
        pending[key] = value
        let ticket = (revision[key] ?? 0)+1
        revision[key] = ticket
        delayed[key]?.cancel()
        message = "正在应用亮度…"
        let task = DispatchWorkItem { [weak self] in
            guard let self else { return }
            self.worker.async {
                let result = Result { try hardware.set(device, to: value) }
                DispatchQueue.main.async {
                    guard let i = self.devices.firstIndex(where: { $0.id == key }) else { return }
                    if case .success(let confirmed) = result { self.devices[i].value = confirmed }
                    guard self.revision[key] == ticket else { self.updateIcon(); return }
                    self.pending[key] = nil
                    self.delayed[key] = nil
                    switch result {
                    case .success: self.errors.remove(key)
                    case .failure(let error):
                        self.errors.insert(key)
                        self.warnings = Array((self.warnings + [device.name+" · "+error.localizedDescription]).suffix(12))
                    }
                    self.message = !self.errors.isEmpty ? "调节失败，请查看设备诊断" : self.pending.isEmpty ? "亮度已更新" : "正在应用亮度…"
                    self.updateIcon()
                }
            }
        }
        delayed[key] = task
        DispatchQueue.main.asyncAfter(deadline: .now()+0.16, execute: task)
    }
    func setLanguage(_ choice: String) {
        AppLanguage.choice = choice
        objectWillChange.send()
        updateIcon()
    }
    func startup(_ enabled: Bool) {
        do { try login.setEnabled(enabled) } catch { message = error.localizedDescription }
        objectWillChange.send()
    }
}

struct BrightnessView: View {
    @ObservedObject var model: BrightnessApp
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            PanelHeading(name: demo ? tr("明度 · 演示") : tr("明度"), symbol: "sun.max.fill", color: .orange)
            Divider()
            if model.devices.isEmpty { Text(model.busy ? tr("正在检测屏幕…") : tr("连接显示器并开启 DDC/CI，然后点击刷新。")) }
            else {
                ScrollView {
                    VStack(spacing: 12) {
                        ForEach(model.devices) { device in
                            VStack(alignment: .leading, spacing: 6) {
                                HStack(spacing: 12) {
                                    let internalDisplay = device.kind == "apple" || (demo && device.address == "1")
                                    PanelGlyph(symbol: internalDisplay ? "laptopcomputer" : "display",
                                               color: internalDisplay ? .blue : .teal)
                                    Text(device.displayName).fontWeight(.semibold)
                                    Spacer()
                                    Text("\(model.pending[device.id] ?? device.value)%").bold().monospacedDigit()
                                }
                                BrightnessSlider(percent: Binding(get: { model.pending[device.id] ?? device.value },
                                                                  set: { model.request(device, $0) }),
                                                 label: device.displayName+tr("亮度"))
                                    .disabled(model.busy).padding(.leading, 34)
                            }
                            Divider()
                        }
                    }.padding(.trailing, 3)
                }.frame(height: min(CGFloat(model.devices.count)*68, 250))
            }
            Text(tr("所有屏幕 · 快捷亮度")).font(.caption).foregroundStyle(.secondary)
            HStack {
                ForEach([25,60,100], id: \.self) { percent in
                    let selected = !model.devices.isEmpty && model.pending.isEmpty && model.errors.isEmpty && model.devices.allSatisfy { $0.value == percent }
                    Button((percent == 25 ? tr("夜间") : percent == 60 ? tr("日常") : tr("明亮"))+" \(percent)%") {
                        for device in model.devices { model.request(device, percent) }
                    }.tint(selected ? .accentColor : nil)
                    if percent != 100 { Spacer() }
                }
            }.disabled(model.devices.isEmpty || model.busy)
            Divider()
            Picker(tr("状态栏屏幕"), selection: Binding(get: { model.selection }, set: model.setTarget)) {
                Text(tr("所有显示器")).tag("all")
                ForEach(model.devices) { Text($0.displayName).tag($0.id) }
            }
            Text(tr(model.message)).font(.caption).foregroundStyle(.secondary)
            HStack { Button(tr("刷新"), action: model.scan).disabled(model.busy || !model.pending.isEmpty); Spacer()
                Button(tr("设备诊断")) { model.diagnostics.toggle() }; Spacer(); Button(tr("退出")) { NSApp.terminate(nil) } }
            if model.diagnostics {
                ScrollView { Text((model.warnings.map(tr)+[tr("连接或唤醒显示器后请刷新。外接屏幕需开启 DDC/CI。")]).joined(separator: "\n"))
                    .frame(maxWidth: .infinity, alignment: .leading).font(.caption).textSelection(.enabled) }.frame(height: 72)
            }
            Picker(AppLanguage.english ? "Language" : "语言", selection: Binding(
                get: { AppLanguage.choice }, set: model.setLanguage)) {
                ForEach(Array(zip(AppLanguage.choices, AppLanguage.names)), id: \.0) { Text($0.1).tag($0.0) }
            }
            Toggle(tr("登录系统时启动"), isOn: Binding(get: { model.login.enabled }, set: model.startup)).disabled(demo)
        }.padding(18).frame(width: AppLanguage.english ? 400 : 360).fixedSize(horizontal: false, vertical: true)
    }
}

if args.contains("--version") { print(Bundle.main.infoDictionary?["CFBundleShortVersionString"] ?? ""); exit(0) }
if args.contains("--diagnose") {
    let scan = hardware.scan()
    print(String(decoding: try JSONEncoder().encode(scan), as: UTF8.self))
    exit(scan.displays.isEmpty ? 1 : 0)
}
if args.contains("--smoke-test") && !demo { exit(2) }
try FileManager.default.createDirectory(at: config, withIntermediateDirectories: true)
instanceFD = open(lockURL.path, O_RDWR | O_CREAT | O_NOFOLLOW, 0o600)
guard instanceFD >= 0 else { throw HardwareError("无法建立明度会话。") }
if flock(instanceFD, LOCK_EX | LOCK_NB) != 0 {
    for _ in 0..<40 where lseek(instanceFD, 0, SEEK_END) == 0 { Thread.sleep(forTimeInterval: 0.05) }
    DistributedNotificationCenter.default().postNotificationName(notificationName, object: nil, userInfo: nil, deliverImmediately: true)
    exit(0)
}
ftruncate(instanceFD, 0)
let app = NSApplication.shared
app.setActivationPolicy(.accessory)
let delegate = BrightnessApp()
app.delegate = delegate
withExtendedLifetime(delegate) { app.run() }
