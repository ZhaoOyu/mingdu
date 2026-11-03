"""Display-only rules shared by the native frontends; never write hardware."""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class BrightnessSummary:
    value: int | None
    text: str
    description: str


def brightness_summary(displays, confirmed, target="all", errors=None):
    keys = [target] if target in displays else list(displays)
    if not keys:
        return BrightnessSummary(None, "--", "未发现可调节的显示器")
    if errors and any(key in errors for key in keys):
        return BrightnessSummary(None, "!", "部分显示器调节失败，请打开面板查看")
    if any(key not in confirmed for key in keys):
        return BrightnessSummary(None, "--", "正在读取亮度")
    values = [confirmed[key] for key in keys]
    if len(set(values)) > 1:
        return BrightnessSummary(None, "≠", f"{len(keys)} 台显示器亮度不同，请选择单块屏幕查看")
    value = values[0]
    name = displays[keys[0]].name if len(keys) == 1 else "所有显示器"
    return BrightnessSummary(value, str(value), f"{name} · 已确认亮度 {value}%")


def device_kind(kind):
    if kind in ("backlight", "wmi", "apple"):
        return "内置屏幕"
    return "演示设备" if kind == "demo" else "外接显示器"


# A bottom sun bridges the gap, matching the quota bar's arc/number/marker layout.
RING_GAP = 64
RING_SWEEP = 360 - RING_GAP
RING_START = 270 - RING_GAP / 2


def ring_svg(summary, render_text):
    """Filled outlines retain the arc and sun through GTK symbolic recoloring."""
    outer, inner = 11.9, 9.5
    start = 90 + RING_GAP / 2

    def point(angle, radius):
        angle = math.radians(angle)
        return f'{12+radius*math.cos(angle):.4f},{12+radius*math.sin(angle):.4f}'

    def arc(sweep, opacity):
        end, large = start + sweep, int(sweep > 180)
        return (f'<path opacity="{opacity}" d="M{point(start,outer)} A{outer},{outer} 0 {large},1 {point(end,outer)} '
                f'A1.2,1.2 0 0,1 {point(end,inner)} A{inner},{inner} 0 {large},0 {point(start,inner)} '
                f'A1.2,1.2 0 0,1 {point(start,outer)}Z"/>')

    shapes = arc(RING_SWEEP, .28)
    if summary.value is not None and summary.value > 0:
        shapes += arc(RING_SWEEP * summary.value / 100, 1)
    text = render_text(summary.text, 12, 13.7, 9 if len(summary.text) > 2 else 10.5)
    sun = '<circle cx="12" cy="20.1" r="1.45"/>'
    for angle in range(0, 360, 45):
        # Filled capsules rather than SVG strokes: symbolic loaders replace strokes.
        sun += (f'<rect x="11.55" y="16.25" width="0.9" height="1.5" rx="0.45" '
                f'transform="rotate({angle} 12 20.1)"/>')
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">'
            + shapes + text + sun + '</svg>')
