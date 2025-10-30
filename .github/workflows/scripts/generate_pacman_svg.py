#!/usr/bin/env python3
"""
.generate_pacman_svg.py
Pure-Python SVG generator for a Pac-Man animation frame (or slightly different each run).
Writes pacman.svg to repo root.
"""

import yaml
import math
from datetime import datetime
import os
import sys

# ---------- Helper: safe load yaml ----------
def load_config(path="config.yml"):
    if not os.path.exists(path):
        # default fallback
        return {
            "theme":{"width":400,"height":100,"background":"#000000","pacman_color":"#FFDF00","dot_color":"#FFFFFF","ghost_colors":["#FF6666","#66CCFF","#FFB86B","#BDBDFF"]},
            "layout":{"dot_count":7,"dot_spacing":50},
            "animation":{"duration_s":5,"mouth_speed":8},
            "update":{"stamp_label":True}
        }
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

# ---------- Build SVG ----------
def build_svg(cfg):
    theme = cfg.get("theme", {})
    layout = cfg.get("layout", {})
    anim = cfg.get("animation", {})
    update = cfg.get("update", {})

    W = theme.get("width", 400)
    H = theme.get("height", 100)
    bg = theme.get("background", "#000000")
    pac_color = theme.get("pacman_color", "#FFDF00")
    dot_color = theme.get("dot_color", "#FFFFFF")
    ghost_colors = theme.get("ghost_colors", ["#FF6666","#66CCFF","#FFB86B","#BDBDFF"])

    dot_count = layout.get("dot_count", 7)
    dot_spacing = layout.get("dot_spacing", 50)

    duration = anim.get("duration_s", 5)
    mouth_speed = anim.get("mouth_speed", 8)

    # Use current UTC time to vary pacman position so successive runs show motion
    now = datetime.utcnow()
    # t between 0 and duration (use seconds + minutes to get variety)
    t_seconds = (now.minute * 60 + now.second) % (duration * 100 if duration>0 else 5)
    # Map t to x position along path
    path_left = 20
    path_right = W - 20
    # Normalize within duration
    if duration <= 0:
        p = 0
    else:
        p = (t_seconds % (duration*100)) / (duration*100)  # 0..1
    pac_x = path_left + (path_right - path_left) * p

    # Mouth angle varies with time
    mouth_phase = (now.second + now.microsecond/1e6) * mouth_speed
    mouth_open_deg = 25 * abs(math.sin(math.radians(mouth_phase * 30)))

    # Build dot positions (y centered)
    center_y = H // 2
    first_dot_x = 60
    dots = []
    for i in range(dot_count):
        x = first_dot_x + i * dot_spacing
        # compute a tiny flicker based on time so dots can flash
        phase = (now.second + i*0.3) % duration if duration>0 else 0
        opacity = 1.0 - (0.2 * math.sin((now.second + i) * 0.6))
        opacity = max(0.15, min(1.0, opacity))
        dots.append((x, center_y, opacity))

    # optional ghosts — simple positions
    ghosts = []
    gbase_x = W*0.6
    for i, col in enumerate(ghost_colors):
        gx = gbase_x + i*22
        gy = center_y - 18 + ((-1)**i) * 6 * math.sin(now.second * 0.5 + i)
        ghosts.append((gx, gy, col))

    # Build the SVG markup using <animateTransform> for mouth & translate for pacman
    svg_parts = []
    svg_parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
    svg_parts.append(f'<rect width="{W}" height="{H}" fill="{bg}" />')

    # Dots
    svg_parts.append(f'<g id="dots" fill="{dot_color}">')
    for (x,y,op) in dots:
        svg_parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{dot_color}" fill-opacity="{op:.2f}"/>')
    svg_parts.append('</g>')

    # Ghosts (decorative)
    svg_parts.append('<g id="ghosts">')
    for (gx,gy,gcol) in ghosts:
        svg_parts.append(f'<g transform="translate({gx:.1f},{gy:.1f})">')
        # simple ghost body using path
        svg_parts.append(f'<path d="M-10,6 Q-10,-8 0,-12 Q10,-8 10,6 V10 Q5,8 0,10 Q-5,8 -10,10 Z" fill="{gcol}" />')
        svg_parts.append(f'<circle cx="-4" cy="-4" r="3" fill="#fff"/><circle cx="4" cy="-4" r="3" fill="#fff"/>')
        svg_parts.append('</g>')
    svg_parts.append('</g>')

    # Pac-Man group (drawn as a wedge). We'll animate mouth rotation for subtle effect.
    # Compose mouth wedge path based on mouth_open_deg
    # Use a semicircle approximation by arc. We'll render a wedge using arc endpoints (simplified).
    r = 16
    angle = math.radians(mouth_open_deg)
    # Path: move to center, line to arc start, arc to arc end, close
    x0 = pac_x
    y0 = center_y
    sx = x0 + r * math.cos(angle)
    sy = y0 - r * math.sin(angle)
    ex = x0 + r * math.cos(-angle)
    ey = y0 - r * math.sin(-angle)
    # large-arc-flag 0 small arc, sweep 1
    mouth_path = f'M {x0:.2f},{y0:.2f} L {sx:.2f},{sy:.2f} A {r},{r} 0 0,1 {ex:.2f},{ey:.2f} Z'

    svg_parts.append('<g id="pacman">')
    svg_parts.append(f'<path d="{mouth_path}" fill="{pac_color}" stroke="none" />')
    # small eye
    eye_x = x0 + 6
    eye_y = y0 - 6
    svg_parts.append(f'<circle cx="{eye_x:.2f}" cy="{eye_y:.2f}" r="2" fill="#000" />')
    # subtle mouth animation using animateTransform rotation
    svg_parts.append(f'''
      <animateTransform xlink:href="#pacman" attributeName="transform" type="translate"
                        from="0 0" to="0 0" dur="0.0s" repeatCount="1"/>
    ''')
    svg_parts.append('</g>')

    if update.get("stamp_label", True):
        stamp = now.strftime("%Y-%m-%d %H:%M:%S UTC")
        svg_parts.append(f'<text x="10" y="{H-8}" fill="#888" font-family="monospace" font-size="10">Updated: {stamp}</text>')

    svg_parts.append('</svg>')
    return "\n".join(svg_parts)


def main():
    cfg = load_config("config.yml")
    svg = build_svg(cfg)
    out_path = "pacman.svg"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Wrote {out_path}")

if __name__ == "__main__":
    main()
