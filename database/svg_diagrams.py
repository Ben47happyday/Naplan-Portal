"""
Generates small, self-contained SVG diagrams for Numeracy questions that
benefit from a visual aid (shapes, clocks, coins, rectangles, triangles).

Design rule: every diagram shows only the quantities GIVEN in the question,
never the quantity being asked for — so a diagram can never leak the answer.
Where the asked-for value would normally be labelled, a "?" is used instead.

Each function returns a standalone <svg>...</svg> string using the site's
palette (cream background, warm brown ink, orange accent) so it drops
straight into an <img> tag or inline into a page.
"""

import math

INK = "#3B3024"
ACCENT = "#BA7517"
FILL = "#FBF3E7"
LINE = "#D8C6A8"

_HEADER = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 220" width="320" height="220">'
_FOOTER = "</svg>"


def _wrap(body, bg=True):
    bg_rect = f'<rect x="0" y="0" width="320" height="220" rx="12" fill="{FILL}"/>' if bg else ""
    return f'{_HEADER}{bg_rect}{body}{_FOOTER}'


def _text(x, y, s, size=16, weight="600", anchor="middle", fill=INK):
    return (f'<text x="{x}" y="{y}" font-family="Verdana, sans-serif" font-size="{size}" '
            f'font-weight="{weight}" text-anchor="{anchor}" fill="{fill}">{s}</text>')


def shape_svg(shape_name):
    """A single named polygon (or circle), centred, unlabeled sides."""
    cx, cy, r = 160, 110, 70
    name = shape_name.lower()
    special = {"triangle": 3, "square": 4, "rectangle": 4, "pentagon": 5, "hexagon": 6,
               "heptagon": 7, "octagon": 8, "nonagon": 9}

    if name == "circle":
        body = f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{ACCENT}" stroke-width="4"/>'
    elif name == "rectangle":
        w, h = 140, 90
        body = (f'<rect x="{cx - w/2}" y="{cy - h/2}" width="{w}" height="{h}" '
                f'fill="none" stroke="{ACCENT}" stroke-width="4"/>')
    else:
        sides = special.get(name, 5)
        pts = []
        start = -math.pi / 2 if sides % 2 else -math.pi / 2 + math.pi / sides
        for i in range(sides):
            ang = start + 2 * math.pi * i / sides
            pts.append(f"{cx + r*math.cos(ang):.1f},{cy + r*math.sin(ang):.1f}")
        body = f'<polygon points="{" ".join(pts)}" fill="none" stroke="{ACCENT}" stroke-width="4"/>'

    body += _text(cx, 205, shape_name.capitalize(), size=15)
    return _wrap(body)


def shape_options_svg(names):
    """Several small unlabeled shapes side by side, for 'which shape is X' items."""
    n = len(names)
    cell_w = 320 / n
    parts = []
    for i, name in enumerate(names):
        cx, cy, r = cell_w * i + cell_w / 2, 100, min(cell_w, 90) * 0.32
        low = name.lower()
        letter = chr(65 + i)
        if low == "circle":
            parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{ACCENT}" stroke-width="3"/>')
        elif low == "rectangle":
            w, h = r * 2.2, r * 1.4
            parts.append(f'<rect x="{cx-w/2}" y="{cy-h/2}" width="{w}" height="{h}" fill="none" stroke="{ACCENT}" stroke-width="3"/>')
        elif low == "square":
            s = r * 1.6
            parts.append(f'<rect x="{cx-s/2}" y="{cy-s/2}" width="{s}" height="{s}" fill="none" stroke="{ACCENT}" stroke-width="3"/>')
        elif low == "triangle":
            pts = f"{cx},{cy-r} {cx-r*0.9:.1f},{cy+r*0.7:.1f} {cx+r*0.9:.1f},{cy+r*0.7:.1f}"
            parts.append(f'<polygon points="{pts}" fill="none" stroke="{ACCENT}" stroke-width="3"/>')
        parts.append(_text(cx, 165, letter, size=15, fill="#8A7A67"))
    return _wrap("".join(parts))


def clock_svg(hour, minute):
    cx, cy, r = 160, 105, 78
    body = f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="white" stroke="{INK}" stroke-width="3"/>'
    for h in range(1, 13):
        ang = math.pi / 6 * (h - 3)
        tx, ty = cx + (r - 18) * math.cos(ang), cy + (r - 18) * math.sin(ang)
        body += _text(tx, ty + 5, str(h), size=13, weight="500")
    for m in range(60):
        ang = math.pi / 30 * m
        r1, r2 = (r - 10, r - 4) if m % 5 else (r - 14, r - 4)
        x1, y1 = cx + r1 * math.cos(ang), cy + r1 * math.sin(ang)
        x2, y2 = cx + r2 * math.cos(ang), cy + r2 * math.sin(ang)
        body += f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{LINE}" stroke-width="1.5"/>'

    hour12 = hour % 12
    hour_ang = math.pi / 6 * (hour12 + minute / 60) - math.pi / 2
    min_ang = math.pi / 30 * minute - math.pi / 2
    hx, hy = cx + r * 0.5 * math.cos(hour_ang), cy + r * 0.5 * math.sin(hour_ang)
    mx, my = cx + r * 0.75 * math.cos(min_ang), cy + r * 0.75 * math.sin(min_ang)
    body += f'<line x1="{cx}" y1="{cy}" x2="{hx:.1f}" y2="{hy:.1f}" stroke="{INK}" stroke-width="5" stroke-linecap="round"/>'
    body += f'<line x1="{cx}" y1="{cy}" x2="{mx:.1f}" y2="{my:.1f}" stroke="{ACCENT}" stroke-width="3.5" stroke-linecap="round"/>'
    body += f'<circle cx="{cx}" cy="{cy}" r="4" fill="{INK}"/>'
    body += _text(cx, 205, f"{hour12 if hour12 else 12}:{minute:02d}", size=16)
    return _wrap(body)


def coins_svg(values_cents):
    n = len(values_cents)
    cell_w = 320 / n
    parts = []
    for i, v in enumerate(values_cents):
        cx, cy = cell_w * i + cell_w / 2, 95
        r = 42 if v < 100 else 48
        label = f"${v//100}" if v >= 100 else f"{v}c"
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#F4E3BC" stroke="{ACCENT}" stroke-width="3"/>')
        parts.append(_text(cx, cy + 6, label, size=17))
    return _wrap("".join(parts))


def rectangle_svg(length, width, mode):
    max_w, max_h = 220, 130
    scale = min(max_w / length, max_h / width)
    w, h = length * scale, width * scale
    x, y = 160 - w / 2, 100 - h / 2

    if mode == "area":
        rect = (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
                f'fill="{ACCENT}" fill-opacity="0.25" stroke="{ACCENT}" stroke-width="3"/>')
    else:
        rect = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="none" stroke="{ACCENT}" stroke-width="4"/>'

    body = rect
    body += _text(160, y - 12, f"{length} cm", size=15)
    body += _text(x - 18, 105, f"{width} cm", size=15, anchor="middle")
    return _wrap(body)


def triangle_angles_svg(angle_a, angle_b, third_label="?"):
    p1, p2, p3 = (160, 40), (60, 180), (260, 180)
    body = f'<polygon points="{p1[0]},{p1[1]} {p2[0]},{p2[1]} {p3[0]},{p3[1]}" fill="none" stroke="{ACCENT}" stroke-width="4"/>'
    body += _text(p1[0], p1[1] - 10, f"{angle_a}°", size=15)
    body += _text(p2[0] - 8, p2[1] + 20, f"{angle_b}°", size=15, anchor="end")
    body += _text(p3[0] + 8, p3[1] + 20, f"{third_label}", size=15, anchor="start")
    return _wrap(body)


def right_triangle_svg(leg_a, leg_b, hyp_label="?"):
    p1, p2, p3 = (70, 170), (70, 50), (250, 170)
    body = f'<polygon points="{p1[0]},{p1[1]} {p2[0]},{p2[1]} {p3[0]},{p3[1]}" fill="none" stroke="{ACCENT}" stroke-width="4"/>'
    body += f'<rect x="70" y="150" width="20" height="20" fill="none" stroke="{INK}" stroke-width="2"/>'
    body += _text(45, 115, f"{leg_a} cm", size=15, anchor="middle")
    body += _text(160, 190, f"{leg_b} cm", size=15, anchor="middle")
    mx, my = (p2[0] + p3[0]) / 2, (p2[1] + p3[1]) / 2
    body += _text(mx + 20, my - 10, f"{hyp_label}", size=15, anchor="middle")
    return _wrap(body)


def right_triangle_trig_svg(angle_deg, hyp, opposite_label="?"):
    p1, p2, p3 = (70, 170), (70, 50), (250, 170)
    body = f'<polygon points="{p1[0]},{p1[1]} {p2[0]},{p2[1]} {p3[0]},{p3[1]}" fill="none" stroke="{ACCENT}" stroke-width="4"/>'
    body += f'<rect x="70" y="150" width="20" height="20" fill="none" stroke="{INK}" stroke-width="2"/>'
    body += f'<path d="M 130 170 A 40 40 0 0 0 108 140" fill="none" stroke="{INK}" stroke-width="2"/>'
    body += _text(122, 158, f"{angle_deg}°", size=14, anchor="start")
    body += _text(45, 115, f"{opposite_label}", size=15, anchor="middle")
    mx, my = (p2[0] + p3[0]) / 2, (p2[1] + p3[1]) / 2
    body += _text(mx + 25, my - 10, f"{hyp} cm", size=15, anchor="middle")
    return _wrap(body)


def _clock_face(cx, cy, r, hour, minute):
    body = f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="white" stroke="{INK}" stroke-width="2.5"/>'
    for h in range(1, 13):
        ang = math.pi / 6 * (h - 3)
        tx, ty = cx + (r - 14) * math.cos(ang), cy + (r - 14) * math.sin(ang)
        body += _text(tx, ty + 4, str(h), size=10, weight="500")
    hour12 = hour % 12
    hour_ang = math.pi / 6 * (hour12 + minute / 60) - math.pi / 2
    min_ang = math.pi / 30 * minute - math.pi / 2
    hx, hy = cx + r * 0.45 * math.cos(hour_ang), cy + r * 0.45 * math.sin(hour_ang)
    mx, my = cx + r * 0.68 * math.cos(min_ang), cy + r * 0.68 * math.sin(min_ang)
    body += f'<line x1="{cx}" y1="{cy}" x2="{hx:.1f}" y2="{hy:.1f}" stroke="{INK}" stroke-width="4" stroke-linecap="round"/>'
    body += f'<line x1="{cx}" y1="{cy}" x2="{mx:.1f}" y2="{my:.1f}" stroke="{ACCENT}" stroke-width="3" stroke-linecap="round"/>'
    body += f'<circle cx="{cx}" cy="{cy}" r="3" fill="{INK}"/>'
    return body


def two_clocks_svg(h1, m1, h2, m2, label1="Start", label2="End"):
    """Two small clock faces side by side, for duration/elapsed-time questions.
    Shows only the given start and end times, never the computed duration."""
    r = 68
    body = _clock_face(85, 100, r, h1, m1)
    body += _clock_face(235, 100, r, h2, m2)
    body += _text(85, 192, f"{label1}: {h1 % 12 or 12}:{m1:02d}", size=13)
    body += _text(235, 192, f"{label2}: {h2 % 12 or 12}:{m2:02d}", size=13)
    return _wrap(body)


def number_line_svg(points):
    """A number line with only the given integer points marked (no computed sum)."""
    lo, hi = min(points) - 2, max(points) + 2
    span = max(hi - lo, 1)
    x0, x1 = 20, 300
    step = 1 if span <= 20 else 5 if span <= 60 else 10

    def sx(v):
        return x0 + (v - lo) / span * (x1 - x0)

    body = f'<line x1="{x0}" y1="110" x2="{x1}" y2="110" stroke="{INK}" stroke-width="3"/>'
    start = -(-lo // step) * step if lo % step else lo
    t = start
    while t <= hi:
        x = sx(t)
        body += f'<line x1="{x:.1f}" y1="103" x2="{x:.1f}" y2="117" stroke="{INK}" stroke-width="2"/>'
        body += _text(x, 135, str(t), size=12, fill="#8A7A67")
        t += step
    for p in points:
        x = sx(p)
        body += f'<circle cx="{x:.1f}" cy="110" r="7" fill="{ACCENT}"/>'
        body += _text(x, 90, str(p), size=15)
    return _wrap(body)


def coordinate_point_svg(x, y, note=None):
    """A coordinate grid with only the given starting point plotted — never the
    translated/destination point, so the diagram cannot be measured for the answer."""
    half = max(abs(x), abs(y), 3) + 2
    cx0, cy0 = 160, 100
    scale = 90 / half

    def px(vx):
        return cx0 + vx * scale

    def py(vy):
        return cy0 - vy * scale

    body = ""
    step = 1 if half <= 6 else 2
    g = -((half // step) * step)
    while g <= half:
        if g != 0:
            body += (f'<line x1="{px(g):.1f}" y1="{py(-half):.1f}" x2="{px(g):.1f}" y2="{py(half):.1f}" '
                     f'stroke="{LINE}" stroke-width="1"/>')
            body += (f'<line x1="{px(-half):.1f}" y1="{py(g):.1f}" x2="{px(half):.1f}" y2="{py(g):.1f}" '
                     f'stroke="{LINE}" stroke-width="1"/>')
        g += step
    body += f'<line x1="{px(-half):.1f}" y1="{py(0):.1f}" x2="{px(half):.1f}" y2="{py(0):.1f}" stroke="{INK}" stroke-width="2"/>'
    body += f'<line x1="{px(0):.1f}" y1="{py(-half):.1f}" x2="{px(0):.1f}" y2="{py(half):.1f}" stroke="{INK}" stroke-width="2"/>'
    body += f'<circle cx="{px(x):.1f}" cy="{py(y):.1f}" r="6" fill="{ACCENT}"/>'
    body += _text(px(x) + 16, py(y) - 8, f"A({x}, {y})", size=14, anchor="start")
    if note:
        body += _text(160, 208, note, size=13, fill="#8A7A67")
    return _wrap(body)


def similar_figures_svg(given_dim, scale_factor):
    """Two similar rectangles: the small one labelled with the given side length,
    the large one (scaled by scale_factor) labelled '?' for the unknown side."""
    sw, sh = 70, 46
    lw, lh = min(sw * scale_factor, 170), min(sh * scale_factor, 120)
    sx0, sy0 = 60 - sw / 2, 110 - sh / 2
    lx0, ly0 = 225 - lw / 2, 110 - lh / 2
    body = f'<rect x="{sx0}" y="{sy0}" width="{sw}" height="{sh}" fill="none" stroke="{ACCENT}" stroke-width="3"/>'
    body += f'<rect x="{lx0}" y="{ly0}" width="{lw}" height="{lh}" fill="none" stroke="{ACCENT}" stroke-width="3"/>'
    body += _text(60, sy0 - 10, str(given_dim), size=14)
    body += _text(225, ly0 - 10, "?", size=16)
    body += _text(160, 205, f"scale factor x{scale_factor}", size=13, fill="#8A7A67")
    return _wrap(body)


def rectangle_labeled_svg(length_label, width_label):
    """A rectangle drawn at a fixed size (not to scale) with arbitrary text/expression
    labels on each side — for algebraic (e.g. polynomial) side lengths."""
    w, h = 200, 110
    x, y = 160 - w / 2, 100 - h / 2
    body = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="none" stroke="{ACCENT}" stroke-width="4"/>'
    body += _text(160, y - 12, str(length_label), size=15)
    body += _text(x - 20, 105, str(width_label), size=15, anchor="middle")
    return _wrap(body)


def bar_chart_svg(values, labels=None):
    n = len(values)
    labels = labels or [str(v) for v in values]
    max_v = max(values) or 1
    chart_h = 130
    cell_w = 320 / n
    parts = []
    for i, v in enumerate(values):
        bar_h = (v / max_v) * chart_h
        x = cell_w * i + cell_w * 0.25
        bw = cell_w * 0.5
        y = 175 - bar_h
        parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{bar_h:.1f}" '
                     f'fill="{ACCENT}" fill-opacity="0.55" stroke="{ACCENT}" stroke-width="2"/>')
        parts.append(_text(x + bw / 2, 192, labels[i], size=13))
        parts.append(_text(x + bw / 2, y - 6, str(v), size=12, fill="#8A7A67"))
    parts.append(f'<line x1="10" y1="175" x2="310" y2="175" stroke="{INK}" stroke-width="2"/>')
    return _wrap("".join(parts))
