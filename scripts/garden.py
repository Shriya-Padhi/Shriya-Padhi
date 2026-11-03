#!/usr/bin/env python3
"""Sakura garden for a GitHub profile README.

Renders every picture in assets/ and the README itself from profile.json,
state/stats.json and state/fortune.json. Standard library only, so the
GitHub Actions need no installs.

  python3 scripts/garden.py build            # fetch fresh GitHub data, then render
  python3 scripts/garden.py build --offline  # render from the cached state only
  python3 scripts/garden.py build --time night   # force the header (for previews)
  python3 scripts/garden.py omikuji          # handle a fortune issue (reads env vars)
"""
import argparse
import base64
import datetime as dt
import json
import os
import random
import sys
import textwrap
import urllib.parse
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
FONTS = ASSETS / "fonts"
STATE = ROOT / "state"

SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"
SERIF = "Fraunces, Georgia, 'Times New Roman', serif"
KANJI = "'Fortune JP', 'Noto Serif JP', 'Hiragino Mincho ProN', 'Yu Mincho', serif"

PINK, PINK_DEEP, PINK_CORE = "#f2b5c8", "#e48aa9", "#b4486c"
BARK, LEAF, LEAF_DARK = "#7a5443", "#8dbf8f", "#5f8f68"
CREAM, INK = "#f5ede6", "#3a2a24"


# ---------------------------------------------------------------- helpers
def load_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def save_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def x(s):
    return escape(str(s), {'"': "&quot;"})


_font_cache = {}


def font_css(*which):
    """@font-face rules with the font files embedded, since a README image can't fetch fonts."""
    files = {
        "semibold": ("Fraunces", "normal", 600, "fraunces-semibold.woff2"),
        "italic": ("Fraunces", "italic", 400, "fraunces-italic.woff2"),
        "kanji": ("Fortune JP", "normal", 700, "notoserifjp-fortune.woff2"),
    }
    rules = []
    for key in which:
        fam, style, weight, fn = files[key]
        if fn not in _font_cache:
            _font_cache[fn] = base64.b64encode((FONTS / fn).read_bytes()).decode()
        rules.append(
            f"@font-face{{font-family:'{fam}';font-style:{style};font-weight:{weight};"
            f"src:url(data:font/woff2;base64,{_font_cache[fn]}) format('woff2')}}"
        )
    return "".join(rules)


REDUCED = "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"


def svg(w, h, body, *, title, css="", fonts=(), defs="", vb=None):
    vb = vb or f"0 0 {w} {h}"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="{vb}" role="img" aria-labelledby="t">\n'
        f"<title id=\"t\">{x(title)}</title>\n"
        f"<style>{font_css(*fonts)}{css}{REDUCED}</style>\n"
        f"<defs>{BLOSSOM}{defs}</defs>\n{body}\n</svg>\n"
    )


BLOSSOM = (
    '<g id="bl">'
    + "".join(
        f'<ellipse cx="0" cy="-5" rx="3.8" ry="5.2" fill="{PINK}" transform="rotate({a})"/>'
        for a in (0, 72, 144, 216, 288)
    )
    + f'<circle r="2" fill="{PINK_CORE}"/></g>'
)

PETAL = "M-6,0 C-6,-4 -1,-6 3,-5 L6,-6 L5,-2 C7,1 4,5 0,5 C-4,5 -6,3 -6,0Z"


def bloom(x_, y_, s=1.0, r=0):
    return f'<use href="#bl" transform="translate({x_},{y_}) scale({s}) rotate({r})"/>'


def mono_width(text, size):
    return len(text) * size * 0.61


def write(name, content):
    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS / name).write_text(content, encoding="utf-8")


# ---------------------------------------------------------------- header (day / night)
BRANCH = (
    f'<g fill="none" stroke="{BARK}" stroke-linecap="round">'
    '<path d="M850,8 C770,28 700,46 620,74" stroke-width="8"/>'
    '<path d="M740,36 C730,66 734,96 742,116" stroke-width="4"/>'
    '<path d="M664,60 C658,88 662,110 672,126" stroke-width="3.5"/></g>'
    + bloom(624, 74, 1.4) + bloom(662, 60, 1.1) + bloom(742, 118, 1.4) + bloom(758, 106)
    + bloom(800, 24, 1.3) + bloom(712, 44) + bloom(672, 128, 1.3) + bloom(690, 56, .9) + bloom(828, 16)
)


def lantern(cx, top, color, delay, small=False):
    w, h = (18, 24) if small else (20, 26)
    return (
        f'<circle class="glow" style="animation-delay:{delay}s" cx="{cx}" cy="{top + h / 2 + 10}" r="{22 if not small else 20}" fill="{color}"/>'
        f'<line x1="{cx}" y1="{top}" x2="{cx}" y2="{top + 10}" stroke="#6b5b4b"/>'
        f'<rect x="{cx - w / 2}" y="{top + 10}" width="{w}" height="{h}" rx="9" fill="{color}"/>'
        f'<rect x="{cx - 6}" y="{top + 8}" width="12" height="4" fill="#6b3f2a"/>'
        f'<rect x="{cx - 6}" y="{top + 8 + h}" width="12" height="4" fill="#6b3f2a"/>'
    )


def header(cfg, is_day):
    W, H = 840, 320
    if is_day:
        scene = (
            '<rect width="840" height="320" fill="#f7e4da"/>'
            '<circle cx="560" cy="120" r="40" fill="#f6c28b"/>'
            '<path d="M0,262 Q220,214 440,250 T840,236 L840,320 L0,320 Z" fill="#ecc9c2"/>'
            '<path d="M0,292 Q280,268 560,288 T840,282 L840,320 L0,320 Z" fill="#dfb3ab"/>'
            + BRANCH
        )
        petal, chip_bg, chip_fg, name_c, tag_c, meta_c = "#eea0b9", "#efd3c8", "#5a3f37", INK, "#a03d61", "#6b5048"
        where = f"in {cfg['city']}" if cfg.get("city") else "where I am"
        chip = f"it's daytime {where} · probably around"
    else:
        stars = "".join(
            f'<circle cx="{a}" cy="{b}" r="{r}"/>'
            for a, b, r in [(90, 250, 1.2), (420, 40, 1), (470, 160, 1.3), (520, 230, 1.1), (600, 170, 1.3),
                            (810, 140, 1), (380, 250, 1), (680, 250, 1.2), (250, 280, 1), (780, 250, 1.1)]
        )
        scene = (
            '<rect width="840" height="320" fill="#141b2b"/>'
            f'<g fill="#e9e3ff" opacity=".6">{stars}</g>'
            '<circle cx="744" cy="206" r="26" fill="#f3ead8"/><circle cx="756" cy="198" r="24" fill="#141b2b"/>'
            '<path d="M0,292 Q280,268 560,288 T840,282 L840,320 L0,320 Z" fill="#0d1320"/>'
            f'<g opacity=".85">{BRANCH}</g>'
            '<path d="M360,10 Q490,70 624,62" stroke="#6b5b4b" stroke-width="1.5" fill="none"/>'
            + lantern(412, 31, "#f2a65a", 0) + lantern(491, 53, PINK, 1.1)
            + lantern(571, 62, "#f2a65a", 2.2, small=True)
        )
        petal, chip_bg, chip_fg, name_c, tag_c, meta_c = PINK, "#222c42", "#c9d1d9", CREAM, PINK, "#9ba6b2"
        where = f"in {cfg['city']}" if cfg.get("city") else "where I am"
        chip = f"it's night {where} · back in the morning"

    # petals sit mid-fall in the still frame and drift through when animated
    petals = "".join(
        f'<g transform="translate({px},{py})"><g class="pf" style="animation-duration:{d}s;animation-delay:{dl}s">'
        f'<path d="{PETAL}" fill="{petal}" opacity=".92"/></g></g>'
        for px, py, d, dl in [(560, 200, 16, 0), (650, 60, 19, -5), (735, 170, 14, -9),
                              (815, 255, 21, -12), (480, 120, 18, -7)]
    )
    cw = mono_width(chip, 11.5) + 26
    meta = "".join(
        f'<text x="50" y="{210 + i * 22}" font-family="{MONO}" font-size="13" fill="{meta_c}">{x(m)}</text>'
        for i, m in enumerate(cfg["meta"][:2])
    )
    body = (
        '<clipPath id="card"><rect width="840" height="320" rx="20"/></clipPath>'
        f'<g clip-path="url(#card)">{scene}{petals}</g>'
        f'<rect x="48" y="78" width="{cw:.0f}" height="26" rx="13" fill="{chip_bg}"/>'
        f'<text x="61" y="95.5" font-family="{MONO}" font-size="11.5" fill="{chip_fg}">{x(chip)}</text>'
        f'<text x="46" y="170" font-family="{SERIF}" font-style="italic" font-size="38" fill="{tag_c}">{x(cfg["tagline"])}</text>'
        + meta
    )
    css = (
        ".pf{transform-box:fill-box;transform-origin:center;animation:fall linear infinite}"
        "@keyframes fall{0%{transform:translate(60px,-230px) rotate(0)}50%{transform:translate(0,0) rotate(160deg)}"
        "100%{transform:translate(-70px,230px) rotate(320deg)}}"
        ".glow{transform-box:fill-box;transform-origin:center;opacity:.28;animation:flick 4s ease-in-out infinite}"
        "@keyframes flick{0%,100%{opacity:.18;transform:scale(.95)}50%{opacity:.4;transform:scale(1.1)}}"
    )
    title = f"{cfg['name']}: {cfg['tagline']}. " + ". ".join(cfg["meta"]) + "."
    return svg(W, H, body, title=title, css=css, fonts=("semibold", "italic"))


# ---------------------------------------------------------------- vine divider
def vine(label, theme):
    label_c = PINK if theme == "dark" else "#a03d61"
    end = 640 if len(label) > 12 else 660
    leaves = [(92, 22, -30, .9), (210, 46, 25, 1.5), (380, 20, 30, 2.1), (540, 42, -20, 2.6)]
    leaf_svg = "".join(
        f'<ellipse class="lf" style="animation-delay:{d}s" cx="{a}" cy="{b}" rx="9" ry="4.5" fill="{LEAF}" transform="rotate({r} {a} {b})"/>'
        for a, b, r, d in leaves
    )
    body = (
        f'<path class="vine" pathLength="1" d="M10,34 C90,14 170,52 260,34 S420,14 500,34 S{end - 50},50 {end - 10},34" '
        f'fill="none" stroke="{LEAF_DARK}" stroke-width="2.2" stroke-linecap="round"/>'
        + leaf_svg
        + f'<circle class="lf" style="animation-delay:2.3s" cx="455" cy="27" r="3" fill="{PINK}"/>'
        + f'<ellipse class="lf" style="animation-delay:3.2s" cx="{end}" cy="30" rx="11" ry="5.5" fill="{LEAF}" transform="rotate(-35 {end} 30)"/>'
        + f'<text class="lb" x="{end + 20}" y="40" font-family="{SERIF}" font-style="italic" font-size="20" fill="{label_c}">{x(label)}</text>'
    )
    css = (
        ".vine{stroke-dasharray:1;stroke-dashoffset:0;animation:grow 3.2s ease-in-out .3s both}"
        "@keyframes grow{from{stroke-dashoffset:1}to{stroke-dashoffset:0}}"
        ".lf{animation:fade .8s ease-out both}.lb{animation:fade 1s ease-out 3.3s both}"
        "@keyframes fade{from{opacity:0}to{opacity:1}}"
    )
    return svg(840, 64, body, title=label, css=css, fonts=("italic",))


# ---------------------------------------------------------------- tea house menu
def tea_house(cfg):
    tools = list(cfg["tools"])
    seasonal = (cfg.get("seasonal") or "").strip()
    n = len(tools) + (1 if seasonal else 0)
    pw, gap, top, ph = 52, 8, 62, 222
    total = n * pw + (n - 1) * gap
    x0 = (840 - total) / 2
    plaques = []
    for i, tool in enumerate(tools):
        px = x0 + i * (pw + gap)
        cx = px + pw / 2
        size = 17 if len(tool) <= 11 else 15
        plaques.append(
            f'<rect x="{px:.1f}" y="{top}" width="{pw}" height="{ph}" rx="3" fill="#c9a27a" stroke="#a8825c"/>'
            f'<circle cx="{cx:.1f}" cy="{top + 19}" r="2.5" fill="#5a3f2e"/>'
            f'<text transform="translate({cx - 6:.1f},{top + 34}) rotate(90)" font-family="{SERIF}" font-weight="600" font-size="{size}" fill="#2e211c">{x(tool)}</text>'
        )
    if seasonal:
        px = x0 + len(tools) * (pw + gap)
        cx = px + pw / 2
        plaques.append(
            f'<rect x="{px:.1f}" y="{top}" width="{pw}" height="{ph}" rx="3" fill="{PINK}" stroke="#d98aa5"/>'
            f'<circle cx="{cx:.1f}" cy="{top + 19}" r="2.5" fill="#6b2a40"/>'
            f'<text transform="translate({cx - 4:.1f},{top + 34}) rotate(90)" font-family="{MONO}" font-weight="700" font-size="10" letter-spacing="1.5" fill="#6b2a40">SEASONAL</text>'
            f'<text transform="translate({cx - 5:.1f},{top + 120}) rotate(90)" font-family="{SERIF}" font-style="italic" font-size="15" fill="#3b1626">{x(seasonal[:14])}</text>'
        )
    body = (
        '<rect x=".5" y=".5" width="839" height="299" rx="18" fill="#2a1f1a" stroke="#3a2c24"/>'
        f'<text x="32" y="40" font-family="{MONO}" font-size="12" letter-spacing="1" fill="#c9b4a2">WHAT I WORK WITH</text>'
        + "".join(plaques)
    )
    title = "What I work with: " + ", ".join(tools) + (f". Learning now: {seasonal}." if seasonal else ".")
    return svg(840, 300, body, title=title, fonts=("semibold", "italic") if seasonal else ("semibold",))


# ---------------------------------------------------------------- koi pond
def koi(stats):
    repo = stats.get("current_repo") or "something new"
    label = f"currently · {repo}"
    rw = max(150, mono_width(label, 12.5) + 30)
    pads = "".join(
        f'<path d="M0,0 L{r},-{r * .28:.0f} A{r + 1},{r + 1} 0 1,0 {r},{r * .28:.0f} Z" transform="translate({a},{b}) rotate({t})"/>'
        for a, b, r, t in [(110, 62, 24, 20), (760, 52, 18, 140), (730, 190, 22, 260), (170, 196, 14, 80)]
    )
    resting = "".join(
        f'<path d="{PETAL}" fill="{PINK}" opacity=".85" transform="translate({a},{b}) rotate({t}) scale(.8)"/>'
        for a, b, t in [(250, 160, 30), (450, 44, -20), (590, 112, 60), (700, 124, 10), (380, 206, -40)]
    )
    falling = "".join(
        f'<g transform="translate({a},{b})"><g class="drop" style="animation-delay:{d}s"><path d="{PETAL}" fill="{PINK}" transform="scale(.85)"/></g></g>'
        for a, b, d in [(215, 98, 0), (535, 172, -4), (790, 150, -7.5)]
    )
    fish = (
        f'<line x1="-52" y1="0" x2="-72" y2="0" stroke="#9ba6b2"/>'
        f'<rect x="{-72 - rw:.0f}" y="-12" width="{rw:.0f}" height="24" rx="4" fill="#f3e6d8"/>'
        f'<text x="{-72 - rw / 2:.0f}" y="4.5" text-anchor="middle" font-family="{MONO}" font-size="12.5" fill="{INK}">{x(label)}</text>'
        '<path d="M-32,0 L-54,-13 Q-47,0 -54,13 Z" fill="#f5ede6" opacity=".9"/>'
        '<ellipse cx="7" cy="12" rx="8" ry="3" fill="#f5ede6" opacity=".8" transform="rotate(30 7 12)"/>'
        '<ellipse cx="7" cy="-12" rx="8" ry="3" fill="#f5ede6" opacity=".8" transform="rotate(-30 7 -12)"/>'
        '<ellipse cx="0" cy="0" rx="36" ry="12" fill="#f5ede6"/>'
        '<ellipse cx="10" cy="-3" rx="12" ry="7" fill="#e8743b"/><ellipse cx="-15" cy="2" rx="9" ry="6" fill="#e8743b"/>'
        '<circle cx="28" cy="-3" r="1.5" fill="#222"/>'
    )
    body = (
        '<clipPath id="pond"><rect width="840" height="240" rx="20"/></clipPath>'
        '<g clip-path="url(#pond)"><rect width="840" height="240" fill="#0f2629"/>'
        '<ellipse class="rip" cx="320" cy="70" rx="40" ry="10" fill="none" stroke="#2f5459" stroke-width="1.5"/>'
        '<ellipse class="rip" style="animation-delay:3s" cx="630" cy="180" rx="40" ry="10" fill="none" stroke="#2f5459" stroke-width="1.5"/>'
        f'<g fill="#4f7f5a">{pads}</g>{resting}{falling}'
        f'<g transform="translate({560 if rw < 230 else 600},122)"><g class="swim">{fish}</g></g></g>'
    )
    css = (
        ".swim{animation:swim 28s linear -12s infinite}"
        "@keyframes swim{0%{transform:translate(-640px,0)}25%{transform:translate(-320px,-8px)}50%{transform:translate(0,6px)}"
        "75%{transform:translate(320px,-6px)}100%{transform:translate(640px,0)}}"
        ".drop{transform-box:fill-box;transform-origin:center;animation:drop 11s ease-in infinite}"
        "@keyframes drop{0%{transform:translate(40px,-150px) rotate(-200deg);opacity:0}8%{opacity:1}"
        "70%{transform:translate(0,0) rotate(0);opacity:1}100%{transform:translate(0,0) rotate(0);opacity:0}}"
        ".rip{transform-box:fill-box;transform-origin:center;animation:rip 6s ease-out infinite}"
        "@keyframes rip{0%{transform:scale(.4);opacity:.7}100%{transform:scale(1.6);opacity:0}}"
    )
    return svg(840, 240, body, title=f"A koi swims across a pond trailing a ribbon: currently working on {repo}.", css=css)


# ---------------------------------------------------------------- hanko seals
def hanko(stats):
    red = "#b8322f"

    def num_size(v, base):
        return base if len(str(v)) <= 3 else base - 8 * (len(str(v)) - 3)

    repos, contrib, since = stats.get("repos", 0), stats.get("contributions", 0), stats.get("since", "")
    seal1 = (
        f'<g transform="translate(486,92) rotate(-4)" opacity=".92">'
        f'<rect x="-54" y="-54" width="108" height="108" rx="10" fill="none" stroke="{red}" stroke-width="5"/>'
        f'<rect x="-45" y="-45" width="90" height="90" rx="4" fill="none" stroke="{red}" stroke-width="1.5"/>'
        f'<text y="8" text-anchor="middle" font-family="{SERIF}" font-weight="600" font-size="{num_size(repos, 38)}" fill="{red}">{repos}</text>'
        f'<text y="30" text-anchor="middle" font-family="{MONO}" font-weight="700" font-size="11" letter-spacing="2" fill="{red}">REPOS</text></g>'
    )
    seal2 = (
        f'<g transform="translate(628,92) rotate(3)" opacity=".9">'
        f'<circle r="57" fill="none" stroke="{red}" stroke-width="5"/><circle r="48" fill="none" stroke="{red}" stroke-width="1.5"/>'
        f'<text y="-12" text-anchor="middle" font-family="{MONO}" font-weight="700" font-size="9" letter-spacing="1" fill="{red}">BUILDING SINCE</text>'
        f'<text y="22" text-anchor="middle" font-family="{SERIF}" font-weight="600" font-size="30" fill="{red}">{since}</text></g>'
    )
    seal3 = (
        f'<g transform="translate(770,92) rotate(-1.5)" opacity=".94">'
        f'<rect x="-54" y="-54" width="108" height="108" rx="10" fill="none" stroke="{red}" stroke-width="5"/>'
        f'<rect x="-45" y="-45" width="90" height="90" rx="4" fill="none" stroke="{red}" stroke-width="1.5"/>'
        f'<text y="4" text-anchor="middle" font-family="{SERIF}" font-weight="600" font-size="{num_size(contrib, 38)}" fill="{red}">{contrib}</text>'
        f'<text y="22" text-anchor="middle" font-family="{MONO}" font-weight="700" font-size="8.5" letter-spacing=".3" fill="{red}">CONTRIBUTIONS</text>'
        f'<text y="34" text-anchor="middle" font-family="{MONO}" font-size="8.5" letter-spacing="1" fill="{red}">PAST YEAR</text></g>'
    )
    body = (
        '<rect x=".5" y=".5" width="839" height="183" rx="18" fill="#f6eee3" stroke="#e4d6c3"/>'
        f'<text font-family="{SERIF}" font-style="italic" font-size="21" fill="{INK}">'
        '<tspan x="40" y="84">a few real numbers,</tspan><tspan x="40" y="112">stamped instead of listed</tspan></text>'
        + seal1 + seal2 + seal3
    )
    title = f"{repos} public repositories, building since {since}, {contrib} contributions in the past year."
    return svg(840, 184, body, title=title, fonts=("semibold", "italic"))


# ---------------------------------------------------------------- omikuji
def omikuji(cfg, fortune):
    if fortune:
        kanji, rank, text, who = fortune["kanji"], fortune["name"], fortune["text"], f"drawn by @{fortune['user']}"
    else:
        kanji, rank, text, who = "吉", "blessing", "the first fortune is waiting for you", "no one has drawn yet"
    lines = textwrap.wrap(text, 31)[:2]
    card_h = 150 + 27 * len(lines)
    slips = "".join(
        f'<g class="fl" style="animation-delay:{d}s"><line x1="{a}" y1="{b}" x2="{a}" y2="{b + 12}" stroke="#9ba6b2"/>'
        f'<rect x="{a - 8}" y="{b + 12}" width="16" height="{h}" rx="2" fill="#f5ede6" stroke="#d8c7b4"/></g>'
        for a, b, h, d in [(110, 22, 40, 0), (250, 24, 44, -1.5), (400, 30, 38, -3), (550, 34, 42, -.7), (730, 22, 40, -2.2)]
    )
    buds = "".join(f'<circle cx="{a}" cy="{b}" r="5" fill="{PINK}"/>' for a, b in [(170, 22), (320, 30), (470, 40), (640, 28), (800, 22)])
    text_svg = "".join(
        f'<tspan x="0" y="{-card_h / 2 + 128 + i * 27}">{x(l)}</tspan>' for i, l in enumerate(lines)
    )
    card = (
        f'<g transform="translate(214,{92 + (330 - 92) / 2 + 2}) rotate(-1.5)">'
        f'<rect x="-172" y="{-card_h / 2 + 6}" width="344" height="{card_h}" rx="4" fill="#000" opacity=".35"/>'
        f'<rect x="-174" y="{-card_h / 2}" width="348" height="{card_h}" rx="4" fill="#fbf4ea"/>'
        f'<text y="{-card_h / 2 + 58}" text-anchor="middle" font-family="{KANJI}" font-weight="700" font-size="42" fill="#a8302c">{x(kanji)}</text>'
        f'<text y="{-card_h / 2 + 84}" text-anchor="middle" font-family="{MONO}" font-size="11.5" letter-spacing="2" fill="#7a5a4c">{x(rank.upper())}</text>'
        f'<line x1="-30" y1="{-card_h / 2 + 100}" x2="30" y2="{-card_h / 2 + 100}" stroke="#d8c7b4"/>'
        f'<text text-anchor="middle" font-family="{SERIF}" font-style="italic" font-size="20" fill="#2e211c">{text_svg}</text>'
        f'<text y="{card_h / 2 - 18}" text-anchor="middle" font-family="{SANS}" font-size="12" fill="#6b5048">{x(who)}</text></g>'
    )
    legend = (
        f'<text x="420" y="262" font-family="{SANS}" font-size="12.5" fill="#9ba6b2">'
        + ' · '.join(f'<tspan font-family="{KANJI}" font-weight="700">{k}</tspan> {w}' for k, w in
                     [('大吉', 'great'), ('吉', 'blessing'), ('中吉', 'middle'), ('小吉', 'small'), ('末吉', 'future')])
        + '</text>'
    )
    side = (
        f'<text x="420" y="170" font-family="{SERIF}" font-weight="600" font-size="22" fill="{CREAM}">Before you go, draw a fortune</text>'
        f'<text font-family="{SANS}" font-size="14" fill="#b8c2cc"><tspan x="420" y="202">Yours arrives as a reply on the issue. The latest</tspan>'
        '<tspan x="420" y="223">fortune hangs here for the next visitor to read.</tspan></text>'
        + legend
    )
    body = (
        '<rect x=".5" y=".5" width="839" height="329" rx="18" fill="#121820" stroke="#222b35"/>'
        '<clipPath id="c"><rect width="840" height="330" rx="18"/></clipPath><g clip-path="url(#c)">'
        f'<path d="M-10,30 C200,10 440,46 650,24 S820,20 850,26" stroke="{BARK}" stroke-width="7" fill="none" stroke-linecap="round"/>'
        f"{slips}{buds}</g>{card}{side}"
    )
    css = (
        ".fl{transform-box:fill-box;transform-origin:50% 0;animation:fl 5s ease-in-out infinite}"
        "@keyframes fl{0%,100%{transform:rotate(-4deg)}50%{transform:rotate(4deg)}}"
    )
    title = f"Omikuji: the latest fortune is {rank} ({kanji}): {text}. {who}."
    return svg(840, 330, body, title=title, css=css, fonts=("semibold", "italic", "kanji"))


# ---------------------------------------------------------------- footer: Nara deer
GRASS_BACK = "M0,200 Q2,160 4,120 Q7,160 9,200Z M30,200 Q32,148 24,95 Q37,148 39,200Z M62,200 Q64,165 70,130 Q69,165 71,200Z M95,200 Q97,152 91,105 Q102,152 104,200Z M128,200 Q130,142 134,85 Q135,142 137,200Z M160,200 Q162,162 152,125 Q167,162 169,200Z M195,200 Q197,150 200,100 Q202,150 204,200Z M228,200 Q230,158 223,115 Q235,158 237,200Z M262,200 Q264,145 269,90 Q269,145 271,200Z M296,200 Q298,164 290,128 Q303,164 305,200Z M330,200 Q332,151 334,102 Q337,151 339,200Z M360,200 Q362,170 365,140 Q367,170 369,200Z M400,200 Q402,175 396,150 Q407,175 409,200Z M520,200 Q522,172 526,145 Q527,172 529,200Z M560,200 Q562,169 555,138 Q567,169 569,200Z M600,200 Q602,152 606,104 Q607,152 609,200Z M634,200 Q636,163 629,126 Q641,163 643,200Z M668,200 Q670,146 676,92 Q675,146 677,200Z M702,200 Q704,159 696,118 Q709,159 711,200Z M736,200 Q738,150 741,100 Q743,150 745,200Z M770,200 Q772,165 763,130 Q777,165 779,200Z M804,200 Q806,144 810,88 Q811,144 813,200Z M838,200 Q840,157 833,114 Q845,157 847,200Z M866,200 Q868,151 870,102 Q873,151 875,200Z"
GRASS_FRONT = "M350,200 Q352,180 356,160 Q357,180 359,200Z M372,200 Q374,176 367,152 Q379,176 381,200Z M395,200 Q397,183 399,166 Q402,183 404,200Z M418,200 Q420,178 425,155 Q425,178 427,200Z M442,200 Q444,181 436,162 Q449,181 451,200Z M466,200 Q468,175 471,150 Q473,175 475,200Z M490,200 Q492,182 486,164 Q497,182 499,200Z M514,200 Q516,177 520,154 Q521,177 523,200Z M538,200 Q540,180 533,160 Q545,180 547,200Z M562,200 Q564,178 566,156 Q569,178 571,200Z M12,200 Q14,175 17,150 Q19,175 21,200Z M48,200 Q50,181 44,162 Q55,181 57,200Z M110,200 Q112,172 116,145 Q117,172 119,200Z M180,200 Q182,179 175,158 Q187,179 189,200Z M245,200 Q247,174 249,148 Q252,174 254,200Z M310,200 Q312,180 316,160 Q317,180 319,200Z M620,200 Q622,176 615,152 Q627,176 629,200Z M690,200 Q692,180 696,160 Q697,180 699,200Z M752,200 Q754,172 748,145 Q759,172 761,200Z M820,200 Q822,178 825,156 Q827,178 829,200Z M856,200 Q858,182 850,164 Q863,182 865,200Z"

DEER_BODY = (
    '<ellipse cx="497" cy="152" rx="34" ry="30" fill="#a26f4c"/>'
    '<ellipse cx="450" cy="160" rx="70" ry="29" fill="#b07a55"/>'
    '<ellipse cx="448" cy="179" rx="46" ry="7" fill="#d9b08f" opacity=".55"/>'
    '<ellipse cx="530" cy="142" rx="7" ry="5" fill="#f3dfc8"/>'
    '<g fill="#f3dfc8" opacity=".8"><circle cx="462" cy="147" r="3"/><circle cx="480" cy="140" r="2.6"/>'
    '<circle cx="496" cy="137" r="2.8"/><circle cx="510" cy="149" r="2.6"/><circle cx="472" cy="158" r="2.4"/></g>'
    '<ellipse cx="392" cy="182" rx="26" ry="7" fill="#a26f4c"/>'
)
DEER_ASLEEP = (
    '<path d="M396,166 C384,140 398,122 422,124 L436,144 Z" fill="#b07a55"/>'
    '<ellipse cx="432" cy="132" rx="19" ry="13" fill="#b07a55" transform="rotate(15 432 132)"/>'
    '<ellipse cx="449" cy="138" rx="8" ry="6" fill="#8f5f40"/><circle cx="455" cy="139" r="2" fill="#3a2a24"/>'
    '<ellipse cx="418" cy="120" rx="10" ry="5" fill="#a26f4c" transform="rotate(-30 418 120)"/>'
    '<ellipse cx="418" cy="120" rx="6" ry="2.5" fill="#e9c3a6" transform="rotate(-30 418 120)"/>'
    '<path d="M426,129 Q430,133 434,129" fill="none" stroke="#3a2a24" stroke-width="1.5" stroke-linecap="round"/>'
)
DEER_AWAKE = (
    '<path d="M398,168 C390,140 394,114 404,98 L422,102 C416,126 418,146 434,154 Z" fill="#b07a55"/>'
    '<g class="bow">'
    '<ellipse cx="400" cy="90" rx="18" ry="11" fill="#b07a55" transform="rotate(-15 400 90)"/>'
    '<ellipse cx="384" cy="95" rx="8" ry="6" fill="#8f5f40"/><circle cx="378" cy="95" r="2" fill="#3a2a24"/>'
    '<ellipse cx="415" cy="78" rx="10" ry="4.5" fill="#a26f4c" transform="rotate(-40 415 78)"/>'
    '<ellipse cx="415" cy="78" rx="6" ry="2.2" fill="#e9c3a6" transform="rotate(-40 415 78)"/>'
    '<circle cx="397" cy="86" r="2" fill="#2a1d18"/><circle cx="397.6" cy="85.4" r=".6" fill="#f5ede6"/></g>'
)


def footer(theme, awake):
    text_c = CREAM if theme == "dark" else INK
    petals = "".join(
        f'<path d="{PETAL}" fill="{PINK}" opacity=".9" transform="translate({a},{b}) rotate({t}) scale(.8)"/>'
        for a, b, t in [(200, 194, 20), (300, 196, -30), (588, 193, 40), (642, 197, -10)]
    )
    if awake:
        deer = DEER_BODY + DEER_AWAKE
        state = "is awake and bowing: someone drew a fortune today"
    else:
        deer = f'<g class="breathe">{DEER_BODY}{DEER_ASLEEP}' + \
            f'<path d="{PETAL}" fill="{PINK}" transform="translate(470,128) rotate(25) scale(.75)"/></g>'
        state = "sleeps curled in tall grass"
    body = (
        f'<text x="440" y="40" text-anchor="middle" font-family="{SERIF}" font-style="italic" font-size="31" fill="{text_c}">thanks for wandering by</text>'
        f'<g transform="translate(0,46)"><path fill="#3f6649" d="{GRASS_BACK}"/>{deer}'
        f'<path fill="#6f9f7a" d="{GRASS_FRONT}"/>{petals}</g>'
    )
    css = (
        ".breathe{transform-box:fill-box;transform-origin:50% 100%;animation:breathe 5.5s ease-in-out infinite}"
        "@keyframes breathe{0%,100%{transform:scaleY(1)}50%{transform:scaleY(1.03)}}"
        ".bow{transform-box:fill-box;transform-origin:85% 95%;animation:bow 6s ease-in-out infinite}"
        "@keyframes bow{0%,55%,100%{transform:rotate(0)}70%,80%{transform:rotate(-16deg)}}"
    )
    return svg(880, 246, body, title=f"Thanks for wandering by. A Nara deer {state}.", css=css, fonts=("italic",))


# ---------------------------------------------------------------- buttons
def btn_fortune():
    body = (
        f'<rect width="196" height="46" rx="23" fill="{PINK}"/>'
        '<rect x="24" y="14" width="8" height="18" rx="1.5" fill="none" stroke="#3b1626" stroke-width="1.7"/>'
        '<line x1="28" y1="18" x2="28" y2="25" stroke="#3b1626" stroke-width="1.5"/>'
        f'<text x="44" y="28.5" font-family="{SANS}" font-weight="600" font-size="15" fill="#3b1626">draw a fortune</text>'
    )
    return svg(196, 46, body, title="Draw a fortune")


def btn_linkedin():
    body = (
        '<rect x="88" y="44" width="10" height="16" fill="#6e4b37"/>'
        '<rect width="186" height="46" rx="6" fill="#8a6048"/><rect y="42" width="186" height="4" rx="2" fill="#6e4b37"/>'
        f'<text x="93" y="28.5" text-anchor="middle" font-family="{SANS}" font-weight="600" font-size="14" letter-spacing=".4" fill="{CREAM}">say hi on LinkedIn</text>'
    )
    return svg(186, 60, body, title="Say hi on LinkedIn")


# ---------------------------------------------------------------- README
def readme(cfg, stats):
    u = cfg["username"]
    issue = (
        f"https://github.com/{u}/{u}/issues/new?"
        + urllib.parse.urlencode(
            {"title": "omikuji: draw a fortune",
             "body": "Just press **Create** below. Your fortune arrives as a reply within a minute. It can take up to 5 minutes to appear on my profile page, where it will hang on the branch until the next visitor draws one."},
            quote_via=urllib.parse.quote,
        )
    )

    def pic(name, alt):
        return (
            "<picture>\n"
            f'  <source media="(prefers-color-scheme: dark)" srcset="assets/{name}-dark.svg">\n'
            f'  <img src="assets/{name}-light.svg" width="100%" alt="{x(alt)}">\n'
            "</picture>"
        )

    return f"""<!-- This README is generated by scripts/garden.py from profile.json. Edit profile.json, not this file. -->

<p align="center">
  <img src="assets/header.svg" width="100%" alt="{x(cfg['name'])}: {x(cfg['tagline'])}. {x('. '.join(cfg['meta']))}.">
</p>

{pic("vine-menu", "today's menu")}

<p align="center">
  <img src="assets/tea-house.svg" width="100%" alt="What I work with: {x(', '.join(cfg['tools']))}.">
</p>

{pic("vine-currently", "currently")}

<p align="center">
  <a href="{stats.get('current_repo_url', f'https://github.com/{u}?tab=repositories')}"><img src="assets/koi.svg" width="100%" alt="A koi swims across a pond carrying the name of the repository I pushed to most recently. Click to open it."></a>
</p>

<p align="center">
  <a href="https://github.com/{u}?tab=repositories"><img src="assets/hanko.svg" width="100%" alt="Hanko seals with my public repository count, the year I started building and my contributions in the past year. Click to see my repositories."></a>
</p>

<p align="center">{cfg['outside_the_code']}</p>

{pic("vine-fortune", "draw a fortune")}

<p align="center">
  <img src="assets/omikuji.svg" width="100%" alt="Omikuji: the most recent fortune drawn by a visitor.">
</p>

<p align="center">
  <a href="{issue}"><img src="assets/btn-fortune.svg" height="46" alt="Draw a fortune"></a>
</p>

<br>

{pic("footer", "Thanks for wandering by. A Nara deer rests in the grass.")}

<p align="center">
  <a href="{cfg['linkedin']}"><img src="assets/btn-linkedin.svg" height="60" alt="Say hi on LinkedIn"></a>
</p>
"""


# ---------------------------------------------------------------- GitHub data
def gh(url, token, data=None):
    req = urllib.request.Request(url, data=data)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "sakura-garden")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def refresh_stats(cfg, stats):
    token = os.environ.get("GITHUB_TOKEN")
    u = cfg["username"]
    try:
        user = gh(f"https://api.github.com/users/{u}", token)
        stats["repos"] = user["public_repos"]
        stats["since"] = int(user["created_at"][:4])
    except Exception as e:
        print(f"note: kept cached profile numbers ({e})", file=sys.stderr)
    if token:
        try:
            q = {"query": "query($l:String!){user(login:$l){contributionsCollection{contributionCalendar{totalContributions}}}}",
                 "variables": {"l": u}}
            res = gh("https://api.github.com/graphql", token, json.dumps(q).encode())
            stats["contributions"] = res["data"]["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]
        except Exception as e:
            print(f"note: kept cached contributions ({e})", file=sys.stderr)
    try:
        events = gh(f"https://api.github.com/users/{u}/events/public?per_page=50", token)
        for ev in events:
            name = ev.get("repo", {}).get("name", "")
            if ev.get("type") == "PushEvent" and name.lower() != f"{u}/{u}".lower():
                stats["current_repo_url"] = f"https://github.com/{name}"
                break
    except Exception as e:
        print(f"note: kept cached current repo ({e})", file=sys.stderr)
    return stats


# ---------------------------------------------------------------- commands
def is_daytime(cfg, now=None):
    now = now or dt.datetime.now(ZoneInfo(cfg["timezone"]))
    return cfg["day_starts"] <= now.hour < cfg["night_starts"]


def deer_awake(fortune, now=None):
    if not fortune or not fortune.get("drawn_at"):
        return False
    now = now or dt.datetime.now(dt.timezone.utc)
    drawn = dt.datetime.fromisoformat(fortune["drawn_at"].replace("Z", "+00:00"))
    return now - drawn < dt.timedelta(hours=24)


def build(offline=False, force_time=None):
    cfg = load_json(ROOT / "profile.json")
    stats = load_json(STATE / "stats.json", {})
    fortune = load_json(STATE / "fortune.json")
    if not offline:
        before = dict(stats)
        stats = refresh_stats(cfg, dict(stats))
        if {k: v for k, v in stats.items() if k != "updated"} != {k: v for k, v in before.items() if k != "updated"}:
            stats["updated"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            save_json(STATE / "stats.json", stats)
    day = is_daytime(cfg) if force_time is None else force_time == "day"
    awake = deer_awake(fortune)

    write("header.svg", header(cfg, day))
    for theme in ("dark", "light"):
        write(f"vine-menu-{theme}.svg", vine("today's menu", theme))
        write(f"vine-currently-{theme}.svg", vine("currently", theme))
        write(f"vine-fortune-{theme}.svg", vine("draw a fortune", theme))
        write(f"footer-{theme}.svg", footer(theme, awake))
    write("tea-house.svg", tea_house(cfg))
    write("koi.svg", koi(stats))
    write("hanko.svg", hanko(stats))
    write("omikuji.svg", omikuji(cfg, fortune))
    write("btn-fortune.svg", btn_fortune())
    write("btn-linkedin.svg", btn_linkedin())
    (ROOT / "README.md").write_text(readme(cfg, stats), encoding="utf-8")
    print(f"built: {'day' if day else 'night'} header, deer {'awake' if awake else 'asleep'}, "
          f"koi on {stats.get('current_repo')}")


def draw_omikuji():
    """Called by the omikuji workflow. Reads the issue from env vars set by the workflow."""
    title = os.environ.get("ISSUE_TITLE", "")
    user = os.environ.get("ISSUE_USER", "")
    number = os.environ.get("ISSUE_NUMBER", "0")
    out = os.environ.get("GITHUB_OUTPUT")
    if not title.strip().lower().startswith("omikuji") or not user:
        if out:
            Path(out).open("a").write("drawn=false\n")
        print("not an omikuji issue, skipping")
        return
    data = load_json(ROOT / "scripts" / "fortunes.json")
    rng = random.Random(f"{user}:{number}:{dt.date.today().isoformat()}")
    rank = rng.choices(data["ranks"], weights=[r["weight"] for r in data["ranks"]])[0]
    text = rng.choice(data["fortunes"][rank["kanji"]])
    fortune = {
        "kanji": rank["kanji"], "name": rank["name"], "text": text, "user": user,
        "drawn_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    save_json(STATE / "fortune.json", fortune)
    cfg = load_json(ROOT / "profile.json")
    comment = (
        f"## {rank['kanji']} · {rank['name']}\n\n"
        f"> *{text}*\n\n"
        f"Your fortune is now tied to the branch on [my profile](https://github.com/{cfg['username']}), "
        "where it stays until the next visitor draws one, and the deer is awake to bow to you. "
        "It can take up to 5 minutes to show up there, since GitHub refreshes profile pictures every few minutes. "
        "Thanks for wandering by 🌸"
    )
    (ROOT / "state" / "comment.md").write_text(comment, encoding="utf-8")
    if out:
        Path(out).open("a").write("drawn=true\n")
    build(offline=True)


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--offline", action="store_true")
    b.add_argument("--time", choices=["day", "night"])
    sub.add_parser("omikuji")
    a = p.parse_args()
    if a.cmd == "build":
        build(offline=a.offline, force_time=a.time)
    else:
        draw_omikuji()


if __name__ == "__main__":
    main()
