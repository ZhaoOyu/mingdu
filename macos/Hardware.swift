import Foundation

struct HardwareError: LocalizedError {
    let message: String
    init(_ message: String) { self.message = message }
    var errorDescription: String? { message }
}

struct DisplayDevice: Identifiable, Encodable {
    let name: String, kind: String, address: String
    let maximum: Int
    var value: Int
    var id: String { kind + ":" + address }
    enum CodingKeys: String, CodingKey { case id, name, kind, address, maximum, value }
    func encode(to encoder: Encoder) throws {
        var fields = encoder.container(keyedBy: CodingKeys.self)
        try fields.encode(id, forKey: .id)
        try fields.encode(name, forKey: .name)
        try fields.encode(kind, forKey: .kind)
        try fields.encode(address, forKey: .address)
        try fields.encode(maximum, forKey: .maximum)
        try fields.encode(value, forKey: .value)
    }
}
struct Scan: Encodable {
    var displays = [DisplayDevice]()
    var warnings = [String]()
}

struct Hardware {
    let demo: Bool
    func command(_ tool: String, _ arguments: [String], allowListExit: Bool = false) throws -> String {
        let contents = Bundle.main.bundleURL.appendingPathComponent("Contents")
        let process = Process()
        process.executableURL = contents.appendingPathComponent("Frameworks/helpers/"+tool)
        process.arguments = arguments
        let output = Pipe()
        process.standardOutput = output
        process.standardError = output
        try process.run()
        defer {
            if process.isRunning { kill(process.processIdentifier, SIGKILL) }
            process.waitUntilExit()
        }
        let deadline = ProcessInfo.processInfo.systemUptime+8
        var data = Data()
        while ProcessInfo.processInfo.systemUptime < deadline {
            let fd = output.fileHandleForReading.fileDescriptor
            var descriptor = pollfd(fd: fd, events: Int16(POLLIN), revents: 0)
            guard poll(&descriptor, 1, 100) > 0 else { continue }
            var buffer = [UInt8](repeating: 0, count: 8192)
            let n = read(fd, &buffer, buffer.count)
            if n == 0 {
                while process.isRunning && ProcessInfo.processInfo.systemUptime < deadline {
                    Thread.sleep(forTimeInterval: 0.01)
                }
                guard !process.isRunning else { break }
                guard process.terminationStatus == 0 || (allowListExit && process.terminationStatus == 1) else {
                    throw HardwareError(tool+" 读取或写入失败，请检查连接及 DDC/CI。")
                }
                return String(decoding: data, as: UTF8.self)
            }
            guard n > 0, data.count+n < 1_000_000 else { throw HardwareError(tool+" 返回异常。") }
            data.append(contentsOf: buffer.prefix(n))
        }
        throw HardwareError(tool+" 响应超时，请刷新。")
    }
    func matches(_ pattern: String, _ text: String) -> [[String]] {
        let regex = try! NSRegularExpression(pattern: pattern, options: [.anchorsMatchLines])
        let source = text as NSString
        return regex.matches(in: text, range: NSRange(location: 0, length: source.length)).map { match in
            (1..<match.numberOfRanges).map { source.substring(with: match.range(at: $0)) }
        }
    }
    func apple() throws -> [DisplayDevice] {
        let text = try command("brightness", ["-l"], allowListExit: true)
        let ids = matches(#"^display (\d+): .*?ID (0x[\da-fA-F]+)"#, text)
        return matches(#"^display (\d+): brightness ([\d.]+)\s*$"#, text).compactMap { row in
            guard let id = ids.first(where: { $0[0] == row[0] })?[1], let n = Double(row[1]),
                  (0...1).contains(n), let index = Int(row[0]) else { return nil }
            return DisplayDevice(name: "Apple 背光屏幕 "+String(index+1), kind: "apple", address: id,
                                 maximum: 100, value: Int((100*n).rounded()))
        }
    }
    func intelIDs() throws -> [String] {
        matches(#"CGDisplay ([0-9a-fA-F-]{36}) dispID\(#\d+\)"#, try command("ddcctl", [], allowListExit: true)).map { $0[0].uppercased() }
    }
    func intelIndex(_ address: String) throws -> String {
        let ids = try intelIDs()
        guard let index = ids.firstIndex(of: address), ids.lastIndex(of: address) == index else {
            throw HardwareError("显示器已断开或标识不唯一，请刷新。")
        }
        return String(index+1)
    }
    func ddc(_ name: String, _ kind: String, _ address: String) throws -> DisplayDevice {
        let now: Int?, max: Int?
        if kind == "m1ddc" {
            func read(_ verb: String) throws -> Int? {
                Int(try command(kind, ["display",address,verb,"luminance"]).trimmingCharacters(in: .whitespacesAndNewlines))
            }
            now = try read("get")
            max = try read("max")
        } else {
            let response = try command("ddcctl", ["-d",intelIndex(address),"-b","?"])
            let row = matches(#"I: VCP control #16 \(0x10\) = current:\s*(\d+), max:\s*(\d+)"#, response).first
            now = row.flatMap { Int($0[0]) }
            max = row.flatMap { Int($0[1]) }
        }
        guard let current = now, let maximum = max, (1...65535).contains(maximum),
              (0...maximum).contains(current) else { throw HardwareError("无法读取有效的 DDC/CI 亮度。") }
        return DisplayDevice(name: name, kind: kind, address: address, maximum: maximum,
                             value: Int((Double(current)*100/Double(maximum)).rounded()))
    }
    func scan() -> Scan {
        if demo {
            return Scan(displays: [DisplayDevice(name: "内置显示器", kind: "demo", address: "1", maximum: 100, value: 60),
                                   DisplayDevice(name: "外接显示器", kind: "demo", address: "2", maximum: 100, value: 40)])
        }
        var result = Scan()
        do { result.displays = try apple() }
        catch { result.warnings.append(error.localizedDescription) }
        do {
#if arch(arm64)
            let kind = "m1ddc"
            let candidates = matches(#"^\s*\[\d+\]\s+(.+?)\s+\(([0-9A-Fa-f-]{36})\)\s*$"#, try command(kind, ["display","list"]))
#else
            let kind = "ddcctl"
            let candidates = try intelIDs().enumerated().map { ["外接显示器 "+String($0.offset+1), $0.element] }
#endif
            for row in candidates {
                do { result.displays.append(try ddc(row[0], kind, row[1].uppercased())) }
                catch { result.warnings.append(row[0]+" · "+error.localizedDescription) }
            }
        } catch { result.warnings.append(error.localizedDescription) }
        return result
    }
    func set(_ device: DisplayDevice, to percent: Int) throws -> Int {
        guard (1...100).contains(percent) else { throw HardwareError("亮度需在 1–100 之间。") }
        if demo { return percent }
        if device.kind == "apple" {
            _ = try command("brightness", ["-d",device.address,String(format: "%.2f", Double(percent)/100)])
            guard let confirmed = try apple().first(where: { $0.id == device.id }) else { throw HardwareError("屏幕已断开，请刷新。") }
            return confirmed.value
        }
        let raw = max(1, Int((Double(percent*device.maximum)/100).rounded()))
        if device.kind == "m1ddc" {
            _ = try command("m1ddc", ["display",device.address,"set","luminance",String(raw)])
        } else {
            let reply = try command("ddcctl", ["-d",intelIndex(device.address),"-b",String(raw)])
            if reply.contains("E:") { throw HardwareError("DDC/CI 写入失败。") }
        }
        return try ddc(device.name, device.kind, device.address).value
    }
}
