"""
Generates small, self-contained decorative SVG scenes for Reading and
Writing questions, so those domains get the same kind of visual polish
Numeracy already has via svg_diagrams.py.

Unlike the Numeracy diagrams, these carry no information relevant to the
answer -- they're a themed illustration matching the topic of the passage
or prompt (animals, ocean/environment, school, sport, food, travel,
weather, community), purely to make the quiz page more inviting.

Each scene is built from recognisable parts (a fox has ears, a snout, a
tail; a schoolhouse has a roof, windows and a door; a bus has wheels and
window rows) layered with light shading, rather than flat colour-block
silhouettes -- closer to typical children's-book clip art.

Each builder takes a `seed` (the question_id) and uses it to vary colour,
position and optional secondary elements, so every question that shares a
theme still gets a visually distinct image instead of one image being
stamped across hundreds of questions.

Uses the same palette and 320x220 card convention as svg_diagrams.py so
images from either module look consistent side by side in the quiz UI.
"""

import math
import random

INK = "#3B3024"
ACCENT = "#BA7517"
FILL = "#FBF3E7"
LINE = "#D8C6A8"
ORANGE = "#F7A026"
GREEN = "#6E8F3D"
BLUE = "#7FA7B8"

_HEADER = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 220" width="320" height="220">'
_FOOTER = "</svg>"


def _escape(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _text(x, y, s, size=14, weight="600", anchor="middle", fill=INK):
    return (f'<text x="{x}" y="{y}" font-family="Verdana, sans-serif" font-size="{size}" '
            f'font-weight="{weight}" text-anchor="{anchor}" fill="{fill}">{_escape(s)}</text>')


def _wrap_scene(scene_body, caption, mirror=False):
    bg_rect = f'<rect x="0" y="0" width="320" height="220" rx="12" fill="{FILL}"/>'
    scene = f'<g transform="translate(320,0) scale(-1,1)">{scene_body}</g>' if mirror else scene_body
    cap = _text(160, 202, caption, size=13, fill="#8A7A67")
    return f'{_HEADER}{bg_rect}{scene}{cap}{_FOOTER}'


def _j(rnd, base, amt):
    return base + rnd.uniform(-amt, amt)


def _pick(rnd, options):
    return rnd.choice(options)


ACCENT_SHADES = [ACCENT, "#A8631A", "#C98A2E"]
GREEN_SHADES = [GREEN, "#5C7A32", "#7FA34D"]
ORANGE_SHADES = [ORANGE, "#F0921A", "#FFB24D"]
BLUE_SHADES = [BLUE, "#6C93A5", "#8FB9C9"]
HAIR_SHADES = [INK, "#4A3B26", "#6B4423", "#8A5A2B"]
SKIN = "#E8B98A"


# ---------------------------------------------------------------- helpers

def _sun(cx, cy, r, color, rays=True):
    s = f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{color}"/>'
    if rays:
        for ang in range(0, 360, 45):
            rad = math.radians(ang)
            x1, y1 = cx + (r + 4) * math.cos(rad), cy + (r + 4) * math.sin(rad)
            x2, y2 = cx + (r + 12) * math.cos(rad), cy + (r + 12) * math.sin(rad)
            s += (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                  f'stroke="{color}" stroke-width="3" stroke-linecap="round"/>')
    return s


def _cloud(cx, cy, scale, color, opacity=1):
    s = scale
    op = f' fill-opacity="{opacity}"' if opacity != 1 else ""
    return (
        f'<g{op}>'
        f'<ellipse cx="{cx-15*s:.1f}" cy="{cy+2*s:.1f}" rx="{14*s:.1f}" ry="{10*s:.1f}" fill="{color}"/>'
        f'<ellipse cx="{cx+15*s:.1f}" cy="{cy+2*s:.1f}" rx="{16*s:.1f}" ry="{11*s:.1f}" fill="{color}"/>'
        f'<ellipse cx="{cx:.1f}" cy="{cy-7*s:.1f}" rx="{18*s:.1f}" ry="{13*s:.1f}" fill="{color}"/>'
        f'<ellipse cx="{cx:.1f}" cy="{cy+5*s:.1f}" rx="{32*s:.1f}" ry="{10*s:.1f}" fill="{color}"/>'
        f'</g>'
    )


def _tree(cx, base_y, trunk_h, canopy_r, trunk_color, canopy_color, canopy_color2):
    trunk_w = max(7, canopy_r * 0.26)
    top_y = base_y - trunk_h
    return (
        f'<rect x="{cx-trunk_w/2:.1f}" y="{top_y:.1f}" width="{trunk_w:.1f}" height="{trunk_h:.1f}" rx="2" fill="{trunk_color}"/>'
        f'<circle cx="{cx-canopy_r*0.55:.1f}" cy="{top_y-canopy_r*0.35:.1f}" r="{canopy_r*0.68:.1f}" fill="{canopy_color2}"/>'
        f'<circle cx="{cx+canopy_r*0.55:.1f}" cy="{top_y-canopy_r*0.35:.1f}" r="{canopy_r*0.68:.1f}" fill="{canopy_color2}"/>'
        f'<circle cx="{cx:.1f}" cy="{top_y-canopy_r*0.85:.1f}" r="{canopy_r:.1f}" fill="{canopy_color}"/>'
    )


def _person(cx, base_y, shirt_color, hair_color, rnd, wave=False):
    head_r = 14
    head_cy = base_y - 66
    body_top = head_cy + head_r - 2
    body_bottom = base_y - 16
    p = (
        f'<rect x="{cx-13:.1f}" y="{body_bottom-4:.1f}" width="9" height="20" rx="3" fill="#7A6A50"/>'
        f'<rect x="{cx+4:.1f}" y="{body_bottom-4:.1f}" width="9" height="20" rx="3" fill="#7A6A50"/>'
        f'<ellipse cx="{cx-8.5:.1f}" cy="{base_y:.1f}" rx="8" ry="3.5" fill="#3B3024"/>'
        f'<ellipse cx="{cx+8.5:.1f}" cy="{base_y:.1f}" rx="8" ry="3.5" fill="#3B3024"/>'
        f'<path d="M{cx-20:.1f} {body_bottom:.1f} Q{cx-24:.1f} {body_top+8:.1f} {cx-13:.1f} {body_top:.1f} '
        f'L{cx+13:.1f} {body_top:.1f} Q{cx+24:.1f} {body_top+8:.1f} {cx+20:.1f} {body_bottom:.1f} Z" fill="{shirt_color}"/>'
        f'<path d="M{cx-7:.1f} {body_top:.1f} L{cx:.1f} {body_top+9:.1f} L{cx+7:.1f} {body_top:.1f}" '
        f'fill="none" stroke="{FILL}" stroke-width="2" stroke-linecap="round"/>'
    )
    if wave:
        p += (f'<path d="M{cx+16:.1f} {body_top+6:.1f} Q{cx+30:.1f} {body_top-4:.1f} {cx+27:.1f} {body_top-16:.1f}" '
              f'fill="none" stroke="{shirt_color}" stroke-width="7" stroke-linecap="round"/>'
              f'<circle cx="{cx+27:.1f}" cy="{body_top-19:.1f}" r="4.5" fill="{SKIN}"/>')
    else:
        p += (f'<path d="M{cx+16:.1f} {body_top+6:.1f} Q{cx+24:.1f} {body_top+18:.1f} {cx+18:.1f} {body_top+28:.1f}" '
              f'fill="none" stroke="{shirt_color}" stroke-width="7" stroke-linecap="round"/>')
    p += (f'<path d="M{cx-16:.1f} {body_top+6:.1f} Q{cx-24:.1f} {body_top+18:.1f} {cx-18:.1f} {body_top+28:.1f}" '
          f'fill="none" stroke="{shirt_color}" stroke-width="7" stroke-linecap="round"/>'
          f'<circle cx="{cx:.1f}" cy="{head_cy:.1f}" r="{head_r}" fill="{SKIN}"/>'
          f'<path d="M{cx-14:.1f} {head_cy-2:.1f} Q{cx-15:.1f} {head_cy-24:.1f} {cx:.1f} {head_cy-23:.1f} '
          f'Q{cx+15:.1f} {head_cy-24:.1f} {cx+14:.1f} {head_cy-2:.1f} '
          f'Q{cx+10:.1f} {head_cy-13:.1f} {cx:.1f} {head_cy-12:.1f} Q{cx-10:.1f} {head_cy-13:.1f} {cx-14:.1f} {head_cy-2:.1f} Z" '
          f'fill="{hair_color}"/>'
          f'<circle cx="{cx-5:.1f}" cy="{head_cy+1:.1f}" r="1.6" fill="{INK}"/>'
          f'<circle cx="{cx+5:.1f}" cy="{head_cy+1:.1f}" r="1.6" fill="{INK}"/>'
          f'<path d="M{cx-5:.1f} {head_cy+7:.1f} Q{cx:.1f} {head_cy+11:.1f} {cx+5:.1f} {head_cy+7:.1f}" '
          f'stroke="{INK}" stroke-width="1.6" fill="none" stroke-linecap="round"/>')
    return p


# ------------------------------------------------------------------ themes

def theme_nature_svg(seed=0):
    rnd = random.Random(seed)
    sun_color = _pick(rnd, ORANGE_SHADES)
    canopy1 = _pick(rnd, GREEN_SHADES)
    canopy2 = _pick(rnd, GREEN_SHADES)
    sun_x, sun_y, sun_r = _j(rnd, 55, 10), _j(rnd, 42, 8), _j(rnd, 16, 2)
    tree_x = _j(rnd, 230, 20)
    fox_x, fox_y = _j(rnd, 130, 25), _j(rnd, 168, 6)

    scene = (
        f'<rect x="0" y="182" width="320" height="38" fill="#DCE7C4"/>'
        + _sun(sun_x, sun_y, sun_r, sun_color)
        + _tree(tree_x, 185, 55, _j(rnd, 34, 6), "#7A5C33", canopy1, canopy2)
    )
    if rnd.random() > 0.35:
        scene += _tree(_j(rnd, 285, 12), 190, 32, 18, "#7A5C33", canopy2, canopy1)
    for i in range(6):
        gx = _j(rnd, 15 + i * 50, 15)
        for dx, curve in ((-3, -3), (0, -7), (3, -3)):
            scene += (f'<path d="M{gx+dx:.1f} 218 Q{gx+dx+curve*0.4:.1f} {211:.1f} {gx+dx+curve:.1f} {204:.1f}" '
                      f'stroke="#7C9A54" stroke-width="1.6" fill="none" stroke-linecap="round"/>')

    # owl mascot, standing where the fox used to be: grounded shadow + image
    img_h = 90
    img_w = img_h * (594 / 519)
    img_x = fox_x - img_w / 2
    img_y = (fox_y + 20) - img_h
    scene += (
        f'<ellipse cx="{fox_x:.1f}" cy="{fox_y+18:.1f}" rx="34" ry="7" fill="{INK}" fill-opacity="0.15"/>'
        f'<image href="/images/owl-mascot.png" x="{img_x:.1f}" y="{img_y:.1f}" width="{img_w:.1f}" height="{img_h:.1f}" '
        f'preserveAspectRatio="xMidYMax meet"/>'
    )
    if rnd.random() > 0.4:
        bird_x, bird_y = _j(rnd, 190, 30), _j(rnd, 40, 15)
        bc = _pick(rnd, ACCENT_SHADES)
        scene += (f'<path d="M{bird_x-9:.1f} {bird_y:.1f} Q{bird_x:.1f} {bird_y-9:.1f} {bird_x+9:.1f} {bird_y:.1f}" '
                  f'fill="none" stroke="{bc}" stroke-width="2.4" stroke-linecap="round"/>'
                  f'<path d="M{bird_x+9:.1f} {bird_y-9:.1f} Q{bird_x+18:.1f} {bird_y-13:.1f} {bird_x+27:.1f} {bird_y-9:.1f}" '
                  f'fill="none" stroke="{bc}" stroke-width="2.4" stroke-linecap="round"/>')
    return _wrap_scene(scene, "In the wild", mirror=rnd.random() > 0.5)


def theme_ocean_svg(seed=0):
    rnd = random.Random(seed)
    sun_color = _pick(rnd, ORANGE_SHADES)
    fish_color = _pick(rnd, ACCENT_SHADES)
    weed_color = _pick(rnd, GREEN_SHADES)
    sun_x, sun_y, sun_r = _j(rnd, 255, 15), _j(rnd, 34, 8), _j(rnd, 18, 3)
    fish_x, fish_y = _j(rnd, 130, 22), _j(rnd, 95, 14)

    scene = (
        f'<rect x="0" y="0" width="320" height="70" fill="{BLUE}" fill-opacity="0.18"/>'
        + _sun(sun_x, sun_y, sun_r, sun_color, rays=False)
        + f'<path d="M0 30 Q30 20 60 30 T120 30 T180 30 T240 30 T300 30" fill="none" stroke="{BLUE}" stroke-width="3" stroke-opacity="0.5"/>'
        f'<rect x="0" y="182" width="320" height="38" fill="#E4C98F" fill-opacity="0.55"/>'
    )
    for i in range(10):
        scene += f'<circle cx="{_j(rnd, 20+i*30, 12):.1f}" cy="{_j(rnd, 200, 10):.1f}" r="1.6" fill="{ACCENT}" fill-opacity="0.4"/>'
    for wx in (_j(rnd, 40, 10), _j(rnd, 270, 15)):
        h = _j(rnd, 40, 8)
        scene += (f'<path d="M{wx:.1f} 216 Q{wx-10:.1f} {216-h*0.5:.1f} {wx+2:.1f} {216-h:.1f} '
                  f'Q{wx+12:.1f} {216-h*1.3:.1f} {wx+4:.1f} {216-h*1.7:.1f}" '
                  f'fill="none" stroke="{weed_color}" stroke-width="5" stroke-linecap="round"/>')

    # fish: tail, fins, body, scales, eye
    scene += (
        f'<path d="M{fish_x-22:.1f} {fish_y:.1f} L{fish_x-40:.1f} {fish_y-13:.1f} L{fish_x-34:.1f} {fish_y:.1f} '
        f'L{fish_x-40:.1f} {fish_y+13:.1f} Z" fill="{fish_color}"/>'
        f'<ellipse cx="{fish_x:.1f}" cy="{fish_y:.1f}" rx="26" ry="16" fill="{fish_color}"/>'
        f'<ellipse cx="{fish_x+4:.1f}" cy="{fish_y+5:.1f}" rx="15" ry="8" fill="{FILL}" fill-opacity="0.55"/>'
        f'<polygon points="{fish_x-4:.1f},{fish_y-16:.1f} {fish_x+8:.1f},{fish_y-16:.1f} {fish_x+2:.1f},{fish_y-6:.1f}" fill="{fish_color}"/>'
        f'<polygon points="{fish_x-2:.1f},{fish_y+14:.1f} {fish_x+8:.1f},{fish_y+16:.1f} {fish_x+2:.1f},{fish_y+8:.1f}" fill="{fish_color}"/>'
        f'<path d="M{fish_x-6:.1f} {fish_y-6:.1f} Q{fish_x:.1f} {fish_y-2:.1f} {fish_x-6:.1f} {fish_y+2:.1f}" '
        f'stroke="{INK}" stroke-width="1.2" fill="none" opacity="0.5"/>'
        f'<path d="M{fish_x-14:.1f} {fish_y-2:.1f} Q{fish_x-8:.1f} {fish_y+2:.1f} {fish_x-14:.1f} {fish_y+6:.1f}" '
        f'stroke="{INK}" stroke-width="1.2" fill="none" opacity="0.4"/>'
        f'<circle cx="{fish_x+14:.1f}" cy="{fish_y-4:.1f}" r="5" fill="{FILL}"/>'
        f'<circle cx="{fish_x+16:.1f}" cy="{fish_y-4:.1f}" r="2.4" fill="{INK}"/>'
        f'<path d="M{fish_x+18:.1f} {fish_y-13:.1f} Q{fish_x+22:.1f} {fish_y-2:.1f} {fish_x+16:.1f} {fish_y-13:.1f}" '
        f'fill="{fish_color}"/>'
    )
    if rnd.random() > 0.4:
        f2x, f2y = _j(rnd, 215, 25), _j(rnd, 130, 20)
        f2c = _pick(rnd, ACCENT_SHADES)
        scene += (
            f'<path d="M{f2x-13:.1f} {f2y:.1f} L{f2x-23:.1f} {f2y-8:.1f} L{f2x-23:.1f} {f2y+8:.1f} Z" fill="{f2c}" fill-opacity="0.85"/>'
            f'<ellipse cx="{f2x:.1f}" cy="{f2y:.1f}" rx="15" ry="9" fill="{f2c}" fill-opacity="0.85"/>'
            f'<circle cx="{f2x+8:.1f}" cy="{f2y-2:.1f}" r="1.6" fill="{FILL}"/>'
        )
    return _wrap_scene(scene, "Ocean & environment", mirror=rnd.random() > 0.5)


def theme_school_svg(seed=0):
    rnd = random.Random(seed)
    body_color = _pick(rnd, ACCENT_SHADES)
    roof_color = _pick(rnd, [INK, "#4A3B26"])
    flag_color = _pick(rnd, ORANGE_SHADES)
    cx = _j(rnd, 165, 10)

    scene = (
        _cloud(_j(rnd, 55, 15), _j(rnd, 32, 8), 0.8, "#FFFFFF", 0.7)
        + _cloud(_j(rnd, 260, 15), _j(rnd, 26, 8), 0.6, "#FFFFFF", 0.6)
        + f'<rect x="{cx-72:.1f}" y="100" width="144" height="82" fill="{body_color}"/>'
    )
    for i in range(1, 4):
        scene += f'<line x1="{cx-72:.1f}" y1="{100+i*20:.1f}" x2="{cx+72:.1f}" y2="{100+i*20:.1f}" stroke="{INK}" stroke-width="1" opacity="0.15"/>'
    scene += (
        f'<polygon points="{cx-84:.1f},100 {cx:.1f},52 {cx+84:.1f},100" fill="{roof_color}"/>'
        f'<line x1="{cx-84:.1f}" y1="100" x2="{cx+84:.1f}" y2="100" stroke="#2A2015" stroke-width="2"/>'
        f'<rect x="{cx+30:.1f}" y="34" width="12" height="18" fill="{roof_color}"/>'
    )
    if rnd.random() > 0.3:
        scene += (f'<circle cx="{cx+36:.1f}" cy="28" r="6" fill="#DDD3C2" fill-opacity="0.7"/>'
                   f'<circle cx="{cx+40:.1f}" cy="20" r="8" fill="#DDD3C2" fill-opacity="0.6"/>')
    scene += (
        f'<rect x="{cx-11:.1f}" y="132" width="22" height="50" rx="2" fill="#5A4326"/>'
        f'<circle cx="{cx+7:.1f}" cy="157" r="1.6" fill="{FILL}"/>'
        f'<rect x="{cx-56:.1f}" y="114" width="24" height="22" fill="#EAF3F7"/>'
        f'<line x1="{cx-44:.1f}" y1="114" x2="{cx-44:.1f}" y2="136" stroke="{INK}" stroke-width="1.6"/>'
        f'<line x1="{cx-56:.1f}" y1="125" x2="{cx-32:.1f}" y2="125" stroke="{INK}" stroke-width="1.6"/>'
        f'<rect x="{cx+32:.1f}" y="114" width="24" height="22" fill="#EAF3F7"/>'
        f'<line x1="{cx+44:.1f}" y1="114" x2="{cx+44:.1f}" y2="136" stroke="{INK}" stroke-width="1.6"/>'
        f'<line x1="{cx+32:.1f}" y1="125" x2="{cx+56:.1f}" y2="125" stroke="{INK}" stroke-width="1.6"/>'
        f'<rect x="{cx-4:.1f}" y="44" width="4" height="22" fill="{INK}"/>'
        f'<polygon points="{cx:.1f},46 {cx+18:.1f},51 {cx:.1f},56" fill="{flag_color}"/>'
        f'<polygon points="{cx-84:.1f},182 {cx-64:.1f},100 {cx-52:.1f},100 {cx-68:.1f},182" fill="#C9BB9E"/>'
    )
    scene += _tree(_j(rnd, 268, 8), 182, 34, 20, "#7A5C33", _pick(rnd, GREEN_SHADES), _pick(rnd, GREEN_SHADES))
    return _wrap_scene(scene, "At school", mirror=rnd.random() > 0.5)


def theme_sports_svg(seed=0):
    rnd = random.Random(seed)
    accent = _pick(rnd, ACCENT_SHADES)
    gold = _pick(rnd, ORANGE_SHADES)
    ball_x, ball_y = _j(rnd, 105, 12), _j(rnd, 96, 8)
    ball_r = 34
    trophy_x = _j(rnd, 235, 18)

    scene = f'<rect x="0" y="150" width="320" height="70" fill="#B7CC8E"/>'
    for i in range(6):
        x = i * 55
        scene += f'<rect x="{x:.1f}" y="150" width="27" height="70" fill="#A6BE79" fill-opacity="0.6"/>'
    scene += f'<line x1="10" y1="180" x2="310" y2="180" stroke="#FFFFFF" stroke-width="2" stroke-opacity="0.6"/>'

    scene += (
        f'<ellipse cx="{ball_x+6:.1f}" cy="{ball_y+ball_r-2:.1f}" rx="30" ry="7" fill="{INK}" fill-opacity="0.18"/>'
        f'<circle cx="{ball_x:.1f}" cy="{ball_y:.1f}" r="{ball_r}" fill="white" stroke="{INK}" stroke-width="2.5"/>'
        f'<polygon points="{ball_x:.1f},{ball_y-16:.1f} {ball_x+15:.1f},{ball_y-5:.1f} {ball_x+9:.1f},{ball_y+13:.1f} '
        f'{ball_x-9:.1f},{ball_y+13:.1f} {ball_x-15:.1f},{ball_y-5:.1f}" fill="{INK}"/>'
    )
    for ang in range(0, 360, 72):
        rad = math.radians(ang - 90)
        x1 = ball_x + 15 * math.cos(rad)
        y1 = ball_y + 15 * math.sin(rad)
        x2 = ball_x + ball_r * 0.92 * math.cos(rad)
        y2 = ball_y + ball_r * 0.92 * math.sin(rad)
        scene += f'<path d="M{x1:.1f} {y1:.1f} Q{ball_x + ball_r*0.7*math.cos(rad+0.25):.1f} {ball_y + ball_r*0.7*math.sin(rad+0.25):.1f} {x2:.1f} {y2:.1f}" stroke="{INK}" stroke-width="2" fill="none"/>'
    scene += f'<ellipse cx="{ball_x-10:.1f}" cy="{ball_y-10:.1f}" rx="8" ry="5" fill="white" fill-opacity="0.7"/>'

    scene += (
        f'<rect x="{trophy_x-22:.1f}" y="150" width="44" height="10" rx="2" fill="{accent}"/>'
        f'<rect x="{trophy_x-10:.1f}" y="130" width="20" height="22" fill="{accent}"/>'
        f'<path d="M{trophy_x-20:.1f} 78 Q{trophy_x-20:.1f} 118 {trophy_x-8:.1f} 128 L{trophy_x+8:.1f} 128 '
        f'Q{trophy_x+20:.1f} 118 {trophy_x+20:.1f} 78 Z" fill="{gold}"/>'
        f'<path d="M{trophy_x-20:.1f} 84 Q{trophy_x-38:.1f} 84 {trophy_x-38:.1f} 100 Q{trophy_x-38:.1f} 112 {trophy_x-22:.1f} 110" '
        f'fill="none" stroke="{gold}" stroke-width="5"/>'
        f'<path d="M{trophy_x+20:.1f} 84 Q{trophy_x+38:.1f} 84 {trophy_x+38:.1f} 100 Q{trophy_x+38:.1f} 112 {trophy_x+22:.1f} 110" '
        f'fill="none" stroke="{gold}" stroke-width="5"/>'
        f'<ellipse cx="{trophy_x-6:.1f}" cy="90" rx="4" ry="14" fill="white" fill-opacity="0.35"/>'
        f'<polygon points="{trophy_x:.1f},96 {trophy_x-4:.1f},104 {trophy_x-12:.1f},105 {trophy_x-6:.1f},111 '
        f'{trophy_x-8:.1f},119 {trophy_x:.1f},115 {trophy_x+8:.1f},119 {trophy_x+6:.1f},111 {trophy_x+12:.1f},105 '
        f'{trophy_x+4:.1f},104" fill="{FILL}"/>'
    )
    if rnd.random() > 0.5:
        cone_x = _j(rnd, 30, 12)
        scene += (f'<polygon points="{cone_x:.1f},155 {cone_x-11:.1f},185 {cone_x+11:.1f},185" fill="{_pick(rnd, ORANGE_SHADES)}"/>'
                  f'<rect x="{cone_x-11:.1f}" y="175" width="22" height="5" fill="white"/>')
    return _wrap_scene(scene, "Sport & teamwork", mirror=rnd.random() > 0.5)


def theme_food_svg(seed=0):
    rnd = random.Random(seed)
    cheese = "#F4D889"
    pepperoni = _pick(rnd, ["#B5451F", "#C2582E", "#A83B18"])
    crust = "#D9A45C"
    plate_r = _j(rnd, 88, 5)

    scene = (
        f'<rect x="{130-30}" y="150" width="60" height="18" rx="4" fill="#F3E6D2" stroke="{LINE}" stroke-width="1.5"/>'
        f'<ellipse cx="160" cy="142" rx="{plate_r:.1f}" ry="26" fill="white" stroke="{INK}" stroke-width="2.5"/>'
        f'<ellipse cx="160" cy="142" rx="{plate_r-8:.1f}" ry="20" fill="none" stroke="{LINE}" stroke-width="2"/>'
        f'<path d="M160 122 L{160-52:.1f} {142+18:.1f} A56 22 0 0 0 {160+52:.1f} {142+18:.1f} Z" fill="{crust}"/>'
        f'<path d="M160 128 L{160-42:.1f} {142+13:.1f} A44 16 0 0 0 {160+42:.1f} {142+13:.1f} Z" fill="#C23B22"/>'
        f'<path d="M160 132 L{160-34:.1f} {142+10:.1f} A36 13 0 0 0 {160+34:.1f} {142+10:.1f} Z" fill="{cheese}"/>'
    )
    for i in range(5):
        tx = _j(rnd, 140 + i * 12, 5)
        ty = _j(rnd, 138, 6)
        scene += f'<circle cx="{tx:.1f}" cy="{ty:.1f}" r="4.2" fill="{pepperoni}"/>'
    scene += f'<ellipse cx="{_j(rnd,150,8):.1f}" cy="{_j(rnd,133,4):.1f}" rx="4" ry="2.4" fill="{_pick(rnd, GREEN_SHADES)}"/>'

    for sx in (150, 168):
        scene += (f'<path d="M{sx} 112 Q{sx-6} 100 {sx} 92 Q{sx+6} 84 {sx} 74" '
                  f'stroke="{LINE}" stroke-width="2.5" fill="none" stroke-linecap="round" opacity="0.8"/>')

    scene += (
        f'<rect x="228" y="72" width="6" height="46" rx="2" fill="{INK}"/>'
        f'<path d="M225 72 v18 M231 72 v18 M237 72 v18" stroke="{INK}" stroke-width="3.4" stroke-linecap="round"/>'
        f'<path d="M231 90 v28" stroke="{INK}" stroke-width="3.4" stroke-linecap="round"/>'
        f'<path d="M262 74 Q270 74 270 92 Q270 106 262 112 L262 118 L258 118 L258 74 Z" fill="{INK}"/>'
    )
    return _wrap_scene(scene, "Food & cooking", mirror=rnd.random() > 0.5)


def theme_travel_svg(seed=0):
    rnd = random.Random(seed)
    bus_color = _pick(rnd, ACCENT_SHADES)
    roof_color = _pick(rnd, ORANGE_SHADES)
    bus_x = _j(rnd, 130, 15)

    scene = (
        _cloud(_j(rnd, 55, 15), _j(rnd, 30, 8), 0.7, "#FFFFFF", 0.7)
        + f'<rect x="0" y="164" width="320" height="30" fill="#5A5148"/>'
        f'<rect x="0" y="164" width="320" height="4" fill="#78706600"/>'
    )
    for i in range(8):
        x = (i * 42 + (seed * 7) % 42) % 340 - 10
        scene += f'<rect x="{x:.1f}" y="177" width="16" height="4" fill="#F3E6D2" fill-opacity="0.7"/>'

    scene += (
        f'<rect x="{bus_x-62:.1f}" y="98" width="128" height="58" rx="10" fill="{bus_color}"/>'
        f'<rect x="{bus_x-62:.1f}" y="98" width="128" height="16" rx="8" fill="{roof_color}"/>'
        f'<rect x="{bus_x-48:.1f}" y="108" width="24" height="20" rx="3" fill="#CFE7F0"/>'
        f'<rect x="{bus_x-16:.1f}" y="108" width="24" height="20" rx="3" fill="#CFE7F0"/>'
        f'<rect x="{bus_x+16:.1f}" y="108" width="24" height="20" rx="3" fill="#CFE7F0"/>'
        f'<line x1="{bus_x-42:.1f}" y1="110" x2="{bus_x-36:.1f}" y2="126" stroke="white" stroke-width="2" opacity="0.7"/>'
        f'<line x1="{bus_x-10:.1f}" y1="110" x2="{bus_x-4:.1f}" y2="126" stroke="white" stroke-width="2" opacity="0.7"/>'
        f'<line x1="{bus_x+22:.1f}" y1="110" x2="{bus_x+28:.1f}" y2="126" stroke="white" stroke-width="2" opacity="0.7"/>'
        f'<rect x="{bus_x-62:.1f}" y="140" width="128" height="8" fill="{INK}" opacity="0.15"/>'
        f'<circle cx="{bus_x+48:.1f}" cy="122" r="3.2" fill="{ORANGE}"/>'
    )
    for wx in (bus_x - 38, bus_x + 38):
        scene += (
            f'<circle cx="{wx:.1f}" cy="160" r="13" fill="{INK}"/>'
            f'<circle cx="{wx:.1f}" cy="160" r="7" fill="#B8AFA2"/>'
            f'<circle cx="{wx:.1f}" cy="160" r="2.2" fill="{INK}"/>'
        )
    scene += _tree(_j(rnd, 250, 10), 164, 26, 17, "#7A5C33", _pick(rnd, GREEN_SHADES), _pick(rnd, GREEN_SHADES))
    if rnd.random() > 0.4:
        sx = _j(rnd, 40, 10)
        scene += (f'<rect x="{sx-2:.1f}" y="130" width="4" height="34" fill="#8A8175"/>'
                  f'<circle cx="{sx:.1f}" cy="122" r="14" fill="{_pick(rnd, ACCENT_SHADES)}"/>'
                  f'<rect x="{sx-6:.1f}" y="115" width="12" height="14" fill="white" fill-opacity="0.85"/>')
    return _wrap_scene(scene, "Getting around", mirror=rnd.random() > 0.5)


def theme_weather_svg(seed=0):
    rnd = random.Random(seed)
    sun_color = _pick(rnd, ORANGE_SHADES)
    drop_color = _pick(rnd, BLUE_SHADES)
    sun_x, sun_y = _j(rnd, 90, 15), _j(rnd, 62, 10)
    sun_r = _j(rnd, 30, 4)

    scene = (
        f'<rect x="0" y="0" width="320" height="140" fill="{BLUE}" fill-opacity="0.08"/>'
        + _sun(sun_x, sun_y, sun_r, sun_color)
        + _cloud(190, 90, 1.0, "#C7CFC0", 1)
        + _cloud(185, 84, 1.0, "#FFFFFF", 1)
    )
    n_drops = rnd.choice([3, 4, 5])
    for i in range(n_drops):
        x = _j(rnd, 130 + i * 24, 8)
        y = _j(rnd, 140, 6)
        scene += (f'<path d="M{x:.1f} {y:.1f} Q{x-6:.1f} {y+16:.1f} {x:.1f} {y+20:.1f} '
                  f'Q{x+6:.1f} {y+16:.1f} {x:.1f} {y:.1f} Z" fill="{drop_color}"/>')
    scene += f'<ellipse cx="160" cy="205" rx="90" ry="8" fill="{BLUE}" fill-opacity="0.2"/>'
    scene += f'<path d="M120 205 Q160 198 200 205" stroke="{BLUE}" stroke-width="2" fill="none" opacity="0.5"/>'

    if rnd.random() > 0.55:
        colors = [ORANGE, ACCENT, GREEN, BLUE]
        for i, c in enumerate(colors):
            scene += (f'<path d="M40 190 A{110-i*12} {110-i*12} 0 0 1 280 190" '
                      f'fill="none" stroke="{c}" stroke-width="6" opacity="0.75"/>')
    else:
        ux = _j(rnd, 235, 15)
        uc = _pick(rnd, ACCENT_SHADES)
        scene += (
            f'<line x1="{ux:.1f}" y1="150" x2="{ux:.1f}" y2="195" stroke="{INK}" stroke-width="2.5"/>'
            f'<path d="M{ux-30:.1f} 150 Q{ux-30:.1f} 122 {ux:.1f} 122 Q{ux+30:.1f} 122 {ux+30:.1f} 150 '
            f'Q{ux+20:.1f} 142 {ux+10:.1f} 150 Q{ux:.1f} 142 {ux-10:.1f} 150 Q{ux-20:.1f} 142 {ux-30:.1f} 150 Z" fill="{uc}"/>'
        )
    return _wrap_scene(scene, "Weather & seasons", mirror=rnd.random() > 0.5)


def theme_community_svg(seed=0):
    rnd = random.Random(seed)
    shirt1 = _pick(rnd, ACCENT_SHADES)
    shirt2 = _pick(rnd, GREEN_SHADES)
    hair1 = _pick(rnd, HAIR_SHADES)
    hair2 = _pick(rnd, HAIR_SHADES)
    gap = _j(rnd, 60, 8)
    p1x, p2x = 160 - gap / 2, 160 + gap / 2

    flag_colors = [ACCENT, GREEN, ORANGE, BLUE]
    scene = f'<path d="M20 40 Q160 20 300 40" stroke="{INK}" stroke-width="1.5" fill="none" opacity="0.4"/>'
    for i in range(8):
        fx = 30 + i * 36
        fc = flag_colors[i % len(flag_colors)]
        fy = 40 - (fx - 160) ** 2 / 2400
        scene += f'<polygon points="{fx-9:.1f},{fy:.1f} {fx+9:.1f},{fy:.1f} {fx:.1f},{fy+16:.1f}" fill="{fc}"/>'

    scene += f'<rect x="0" y="188" width="320" height="32" fill="#DCE7C4"/>'
    scene += _person(p1x, 188, shirt1, hair1, rnd, wave=True)
    scene += _person(p2x, 188, shirt2, hair2, rnd, wave=False)

    gx = _j(rnd, 245, 20)
    ribbon = _pick(rnd, ORANGE_SHADES)
    scene += (
        f'<rect x="{gx-20:.1f}" y="160" width="40" height="30" fill="{_pick(rnd, BLUE_SHADES)}"/>'
        f'<rect x="{gx-20:.1f}" y="153" width="40" height="9" fill="{_pick(rnd, BLUE_SHADES)}"/>'
        f'<rect x="{gx-4:.1f}" y="153" width="8" height="37" fill="{ribbon}"/>'
        f'<rect x="{gx-20:.1f}" y="169" width="40" height="8" fill="{ribbon}"/>'
        f'<polygon points="{gx-4:.1f},153 {gx-14:.1f},142 {gx-4:.1f},146" fill="{ribbon}"/>'
        f'<polygon points="{gx+4:.1f},153 {gx+14:.1f},142 {gx+4:.1f},146" fill="{ribbon}"/>'
    )
    for i in range(4):
        sx = _j(rnd, 40 + i * 25, 15)
        sy = _j(rnd, 60 + (i % 2) * 30, 15)
        sc = _pick(rnd, ORANGE_SHADES)
        scene += (f'<path d="M{sx:.1f} {sy-5:.1f} L{sx+1.5:.1f} {sy-1.5:.1f} L{sx+5:.1f} {sy-1.5:.1f} '
                  f'L{sx+2:.1f} {sy+1:.1f} L{sx+3:.1f} {sy+5:.1f} L{sx:.1f} {sy+2.5:.1f} '
                  f'L{sx-3:.1f} {sy+5:.1f} L{sx-2:.1f} {sy+1:.1f} L{sx-5:.1f} {sy-1.5:.1f} '
                  f'L{sx-1.5:.1f} {sy-1.5:.1f} Z" fill="{sc}" opacity="0.85"/>')
    return _wrap_scene(scene, "Community & friends", mirror=rnd.random() > 0.5)


THEMES = {
    "nature": theme_nature_svg,
    "ocean": theme_ocean_svg,
    "school": theme_school_svg,
    "sports": theme_sports_svg,
    "food": theme_food_svg,
    "travel": theme_travel_svg,
    "weather": theme_weather_svg,
    "community": theme_community_svg,
}
