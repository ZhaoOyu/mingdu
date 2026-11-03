import AppKit
import SwiftUI

/// Keep the native continuous track while committing only whole percentages.
struct BrightnessSlider: NSViewRepresentable {
    @Binding var percent: Int
    let label: String
    @Environment(\.isEnabled) private var enabled

    init(percent: Binding<Int>, label: String) {
        _percent = percent
        self.label = label
    }

    func makeNSView(context: Context) -> PercentSlider {
        let slider = PercentSlider()
        slider.minValue = 1
        slider.maxValue = 100
        slider.numberOfTickMarks = 0
        slider.isContinuous = true
        slider.target = context.coordinator
        slider.action = #selector(Coordinator.changed(_:))
        return slider
    }

    func updateNSView(_ slider: PercentSlider, context: Context) {
        context.coordinator.percent = $percent
        slider.doubleValue = Double(max(1, percent))
        slider.isEnabled = enabled
        slider.setAccessibilityLabel(label)
    }

    func makeCoordinator() -> Coordinator { Coordinator($percent) }

    final class Coordinator: NSObject {
        var percent: Binding<Int>
        init(_ percent: Binding<Int>) { self.percent = percent }

        @objc func changed(_ slider: NSSlider) {
            let next = Int(slider.doubleValue.rounded())
            slider.doubleValue = Double(next)
            if percent.wrappedValue != next { percent.wrappedValue = next }
        }
    }
}

final class PercentSlider: NSSlider {
    private func step(by delta: Double) -> Bool {
        guard isEnabled else { return false }
        doubleValue = min(maxValue, max(minValue, doubleValue.rounded() + delta))
        return sendAction(action, to: target)
    }

    override func keyDown(with event: NSEvent) {
        switch event.keyCode {
        case 123, 125: _ = step(by: -1)
        case 124, 126: _ = step(by: 1)
        default: super.keyDown(with: event)
        }
    }

    override func accessibilityPerformIncrement() -> Bool { step(by: 1) }
    override func accessibilityPerformDecrement() -> Bool { step(by: -1) }
}
