#!/usr/bin/env python3
"""Render the profile's Apple-style SVG artwork (light + dark) into assets/gen/.

Run locally or from the daily workflow:  python3 scripts/build.py
Star counts are fetched from the GitHub API (GITHUB_TOKEN optional) and cached
in scripts/stars.json so the build still works offline.
"""
import base64, io, json, os, textwrap, urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
OUT = ASSETS / "gen"
OWNER = "Hitheshkaranth"
FONT = "-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Inter', 'Segoe UI', 'Helvetica Neue', Helvetica, Arial, sans-serif"
MONO = "'SF Mono', ui-monospace, Menlo, Consolas, monospace"

THEMES = {
    "light": dict(bg="#f5f5f7", card="#ffffff", line="#e5e5ea", text="#1d1d1f", sub="#6e6e73",
                  faint="#86868b", link="#0066cc", tile="#ffffff", chrome="#ececee",
                  chrome_line="#d2d2d7", shadow="0.10", glow="0.16"),
    "dark":  dict(bg="#000000", card="#1c1c1e", line="#2c2c2e", text="#f5f5f7", sub="#a1a1a6",
                  faint="#86868b", link="#2997ff", tile="#2c2c2e", chrome="#2c2c2e",
                  chrome_line="#3a3a3c", shadow="0.55", glow="0.28"),
}
# Apple Intelligence-style spectrum
SPECTRUM = ["#0894ff", "#c959dd", "#ff2e54", "#ff9004"]

# ── data ─────────────────────────────────────────────────────────────────────

PROJECTS = {
    "noyce": dict(repo="noyce-ide-dist", logo="noyce-ide.png", accent="#5e5ce6",
        eyebrow="Building now", title="Noyce IDE",
        tagline="Firmware you can prove.",
        desc="An AI-native Code-OSS workbench for safety-critical firmware. Requirements, source, tests, "
             "traceability, MISRA, CBMC, CodeQL, measured MC/DC and hardware tooling in one window.",
        meta="DO-178C evidence · Code-OSS · TypeScript", badge="Stanford × DeepMind Hackathon", stars=False),
    "wirevoice": dict(repo=None, logo="wirevoice.png", accent="#ff9f0a",
        eyebrow="Recognition", title="WireVoice",
        tagline="Ask the schematic. In your language.",
        desc="A voice-first assistant for technicians on complex wiring harness drawings. It names the "
             "terminal, the wire gauge and the exact sheet it came from, across eleven Indian languages.",
        meta="Voice AI · Sarvam · Python", badge="Winner · Sarvam Epoch Buildathon 2026", stars=False),
    "openterminalui": dict(repo="OpenTerminalUI", logo="openterminalui.png", accent="#30d158",
        eyebrow="Open source", title="OpenTerminalUI",
        tagline="A trading terminal you own.",
        desc="A self-hosted financial terminal for traders, researchers and quant teams: multi-market data, "
             "pro charting, derivatives analytics, risk, backtesting, paper trading and an AI research agent.",
        meta="TypeScript · React · Python · FastAPI", badge="MIT"),
    "opentokenmonitor": dict(repo="OpenTokenMonitor", logo="opentokenmonitor.png", accent="#0a84ff",
        eyebrow="Open source", title="OpenTokenMonitor",
        desc="A local-first desktop widget for Claude, Codex and Gemini usage. Quotas, trends and cost "
             "signals in real time. Nothing leaves your machine.",
        meta="Rust · Tauri", badge="MIT"),
    "eds": dict(repo="EmbeddedDisplayStudio", logo="embedded-display-studio.png", accent="#bf5af2",
        eyebrow="Open source", title="EmbeddedDisplayStudio",
        desc="Describe, draw or bring an HMI and ship it to embedded Linux panels. AI design, a C + LVGL "
             "runtime, and atomic SSH deploys with automatic rollback.",
        meta="Python · LVGL · Embedded Linux", badge="MIT"),
    "arinc": dict(repo="arinc-615a-cli-tool-suite", logo="arinc-logo.webp", accent="#64d2ff", wide_logo=True,
        eyebrow="Avionics", title="ARINC 615A Tool Suite",
        tagline="Load software onto aircraft. Over Ethernet.",
        desc="A C++23 implementation of the ARINC 615A data-loading protocol: discover avionics targets, read "
             "part information, transfer software over TFTP and manage ARINC 665 media sets. CLI and Qt 6 GUI.",
        meta="C++23 · Qt 6 · ARINC 615A · ARINC 665 · VxWorks", badge=None),
    "netra-debugger": dict(repo="Netra_System_Debugger_V1", logo="netra-debugger.png", accent="#64d2ff", photo=True,
        eyebrow="Wearables", title="NETRA System Debugger",
        desc="Turns wearable telemetry into sensor diagnostics, live plots, obstacle alerts and an "
             "articulated 3D digital twin.",
        meta="Python · PySide6 · 3D", badge=None),
    "netra-device": dict(repo="Netra_Device_Firmware_V1", logo="netra-device.jpg", accent="#ff9f0a", photo=True,
        eyebrow="Firmware", title="NETRA Device Firmware",
        desc="ESP32-C6 firmware for ultrasonic obstacle ranging and six-axis MPU6050 motion telemetry, "
             "streamed to the companion debugger.",
        meta="C · ESP32-C6 · MPU6050", badge=None),
    "ornith": dict(repo="Ornith-1.5_A3B_Model_DGX_Spark_Setup", logo="ornith.png", accent="#76b900",
        eyebrow="Live on DGX Spark", title="Ornith-1.5-35B-A3B",
        tagline="351.7 tok/s across 16 users.",
        desc="The official 4-bit checkpoint with multi-token-prediction speculative decoding (~87% draft "
             "acceptance) and a real vision tower. Up to 20 concurrent users at 262K context.",
        meta="vLLM 0.24 · NVFP4 + FP8 + MTP · Vision", badge="Apache 2.0"),
    "qwen38": dict(repo="Qwen-3_8_A3B_Model_DGX_Spark_Setup", logo="qwen.png", accent="#76b900", photo=True,
        eyebrow="Self-quantized", title="Qwen3.8-35B-A3B Distill",
        desc="Data-free NVFP4 experts + FP8 attention, streamed one shard at a time in ~20 min. Serves 16 "
             "users at 373 tok/s aggregate.",
        meta="ModelOpt · NVFP4 · vLLM", badge="Apache 2.0"),
    "qwen36": dict(repo="Qwen-3_6_Model_DGX_Spark_Setup", logo="qwen.png", accent="#76b900", photo=True,
        eyebrow="Production recipe", title="Qwen3.6-35B-A3B-NVFP4",
        desc="One-script deployment: 12 concurrent users, 219 tok/s peak, 5.1× faster shared prompts via "
             "prefix caching, Grafana + DCGM included.",
        meta="vLLM · Prometheus · Grafana", badge="Apache 2.0"),
}

# ── helpers ──────────────────────────────────────────────────────────────────

def stars():
    cache = Path(__file__).with_name("stars.json")
    data = json.loads(cache.read_text()) if cache.exists() else {}
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "profile-build"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    for p in PROJECTS.values():
        if not p.get("repo") or p.get("stars") is False:
            continue
        try:
            req = urllib.request.Request(f"https://api.github.com/repos/{OWNER}/{p['repo']}", headers=headers)
            with urllib.request.urlopen(req, timeout=10) as r:
                data[p["repo"]] = json.load(r)["stargazers_count"]
        except Exception as e:  # offline or rate limited: keep the cached value
            print(f"stars: {p['repo']}: {e}")
    cache.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    return data


def data_uri(name, size, photo=False):
    # Resized icons are cached on disk so CI reruns embed byte-identical images.
    cached = OUT / "icons" / f"{Path(name).stem}-{size}{'-sq' if photo else ''}.png"
    if not cached.exists():
        im = Image.open(ASSETS / name).convert("RGBA")
        if photo:  # center-crop to square so it fills the icon
            s = min(im.size)
            l, t = (im.width - s) // 2, (im.height - s) // 2
            im = im.crop((l, t, l + s, t + s))
        im.thumbnail((size, size), Image.LANCZOS)
        cached.parent.mkdir(parents=True, exist_ok=True)
        im.save(cached, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(cached.read_bytes()).decode()


def wrap(text, width):
    return textwrap.wrap(text, width)


def svg(w, h, body, defs="", style=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{w}" height="{h}" viewBox="0 0 {w} {h}" font-family="{FONT}">'
            f'<style>{style}</style><defs>{defs}</defs>{body}</svg>\n')


def shadow_filter(t, fid="shadow", dy=10, blur=18):
    return (f'<filter id="{fid}" x="-20%" y="-20%" width="140%" height="160%">'
            f'<feDropShadow dx="0" dy="{dy}" stdDeviation="{blur}" flood-color="#000" flood-opacity="{t["shadow"]}"/></filter>')


def spectrum_gradient(gid, x2="100%", y2="0%"):
    stops = "".join(f'<stop offset="{i / (len(SPECTRUM) - 1):.2f}" stop-color="{c}"/>' for i, c in enumerate(SPECTRUM))
    return f'<linearGradient id="{gid}" x1="0%" y1="0%" x2="{x2}" y2="{y2}">{stops}</linearGradient>'


def app_icon(p, t, x, y, s):
    """A squircle 'app icon' holding the project logo."""
    r = s * 0.225
    clip = f'<clipPath id="ic"><rect x="{x}" y="{y}" width="{s}" height="{s}" rx="{r}"/></clipPath>'
    if p.get("photo"):
        img = f'<image x="{x}" y="{y}" width="{s}" height="{s}" href="{data_uri(p["logo"], 192, True)}" clip-path="url(#ic)" preserveAspectRatio="xMidYMid slice"/>'
        fill = t["tile"]
    elif p.get("wide_logo"):
        pad = s * 0.12
        img = f'<image x="{x + pad}" y="{y}" width="{s - 2 * pad}" height="{s}" href="{data_uri(p["logo"], 192)}" preserveAspectRatio="xMidYMid meet"/>'
        fill = "#ffffff"
    else:
        pad = s * 0.14
        img = f'<image x="{x + pad}" y="{y + pad}" width="{s - 2 * pad}" height="{s - 2 * pad}" href="{data_uri(p["logo"], 192)}" preserveAspectRatio="xMidYMid meet"/>'
        fill = t["tile"]
    return clip, (f'<g filter="url(#iconShadow)"><rect x="{x}" y="{y}" width="{s}" height="{s}" rx="{r}" fill="{fill}"/></g>'
                  f'{img}<rect x="{x + .5}" y="{y + .5}" width="{s - 1}" height="{s - 1}" rx="{r}" fill="none" stroke="{t["line"]}"/>')


def pill(x, y, text, fg, bg, size=13, bold=True, icon=""):
    w = int(len(text) * size * 0.6) + 26 + (14 if icon else 0)
    return w, (f'<rect x="{x}" y="{y}" width="{w}" height="{size + 15}" rx="{(size + 15) / 2}" fill="{bg}"/>'
               f'{icon}<text x="{x + 13 + (14 if icon else 0)}" y="{y + size + 4}" font-size="{size}" '
               f'font-weight="{600 if bold else 400}" fill="{fg}">{escape(text)}</text>')


def star_icon(x, y, color, s=12):
    # five-point star centred on (x, y)
    import math
    pts = []
    for i in range(10):
        r = s / 2 if i % 2 == 0 else s / 4.6
        a = math.pi / 2 + i * math.pi / 5
        pts.append(f"{x + r * math.cos(a):.1f},{y - r * math.sin(a):.1f}")
    return f'<polygon points="{" ".join(pts)}" fill="{color}"/>'

# ── artwork ──────────────────────────────────────────────────────────────────

def card(key, p, t, theme, star_counts, wide):
    W, H = (1200, 400) if wide else (600, 440)
    acc = p["accent"]
    defs = (shadow_filter(t) + shadow_filter(t, "iconShadow", 6, 10)
            + f'<radialGradient id="glow" cx="{"88%" if wide else "100%"}" cy="0%" r="{"70%" if wide else "95%"}">'
              f'<stop offset="0" stop-color="{acc}" stop-opacity="{t["glow"]}"/><stop offset="1" stop-color="{acc}" stop-opacity="0"/></radialGradient>'
            + '<clipPath id="cardClip"><rect x="16" y="12" width="{w}" height="{h}" rx="30"/></clipPath>'.format(w=W - 32, h=H - 40))
    body = (f'<g filter="url(#shadow)"><rect x="16" y="12" width="{W - 32}" height="{H - 40}" rx="30" fill="{t["card"]}"/></g>'
            f'<g clip-path="url(#cardClip)"><rect x="16" y="12" width="{W - 32}" height="{H - 40}" fill="url(#glow)" class="breathe"/></g>'
            f'<rect x="16.5" y="12.5" width="{W - 33}" height="{H - 41}" rx="30" fill="none" stroke="{t["line"]}"/>')

    if wide:
        ix, iy, isz = 64, 64, 128
        tx, ty = 236, 92
        desc_w = 90
    else:
        ix, iy, isz = 52, 52, 84
        tx, ty = 52, 190
        desc_w = 54
    clip, icon = app_icon(p, t, ix, iy, isz)
    defs += clip
    body += icon

    y = ty
    body += f'<text x="{tx}" y="{y}" font-size="14" font-weight="600" letter-spacing="1.4" fill="{acc}">{escape(p["eyebrow"].upper())}</text>'
    y += 44 if wide else 40
    body += f'<text x="{tx}" y="{y}" font-size="{40 if wide else 32}" font-weight="700" letter-spacing="-0.8" fill="{t["text"]}">{escape(p["title"])}</text>'
    if p.get("tagline") and wide:
        y += 34
        body += f'<text x="{tx}" y="{y}" font-size="23" font-weight="600" letter-spacing="-0.3" fill="{t["sub"]}">{escape(p["tagline"])}</text>'
    y += 16
    for line in wrap(p["desc"], desc_w):
        y += 26
        body += f'<text x="{tx}" y="{y}" font-size="17" fill="{t["sub"]}">{escape(line)}</text>'

    # footer row
    fy = H - 84
    body += f'<text x="{tx if wide else 52}" y="{fy + 19}" font-size="14" fill="{t["faint"]}">{escape(p["meta"])}</text>'
    rx = W - 52
    cta = "View on GitHub ›" if p.get("repo") else ""
    if cta:
        cw = int(len(cta) * 15 * 0.56)
        rx -= cw
        body += f'<text x="{rx}" y="{fy + 19}" font-size="15" font-weight="500" fill="{t["link"]}">{cta}</text>'
        rx -= 16
    # top-right badges
    bx = W - 52
    if p.get("repo") and p.get("stars") is not False and star_counts.get(p["repo"], 0) >= 5:
        txt = f'{star_counts[p["repo"]]:,}'
        w = int(len(txt) * 14 * 0.62) + 50
        bx -= w
        body += (f'<rect x="{bx}" y="52" width="{w}" height="32" rx="16" fill="{t["bg"]}" stroke="{t["line"]}"/>'
                 + star_icon(bx + 20, 68, "#ffcc00", 15)
                 + f'<text x="{bx + 34}" y="73" font-size="14" font-weight="600" fill="{t["text"]}">{txt}</text>')
        bx -= 10
    if p.get("badge"):
        trophy = p["badge"].startswith(("Winner", "Stanford"))
        txt = ("🏆 " if p["badge"].startswith("Winner") else "🎓 " if trophy else "") + p["badge"]
        w = int(len(p["badge"]) * 14 * 0.58) + (52 if trophy else 30)
        bx -= w
        body += (f'<rect x="{bx}" y="52" width="{w}" height="32" rx="16" fill="{acc}" fill-opacity="{0.16 if theme == "dark" else 0.12}"/>'
                 f'<text x="{bx + w / 2}" y="73" text-anchor="middle" font-size="14" font-weight="600" fill="{acc}">{escape(txt)}</text>')

    style = ("@keyframes breathe{0%,100%{opacity:.75}50%{opacity:1}}"
             ".breathe{animation:breathe 6s ease-in-out infinite}")
    return svg(W, H, body, defs, style)


def hero(t, theme):
    """Liquid-glass hero: circuit traces on the left flow into a neural net on the
    right; a row of refracting glass tiles traces the path silicon → intelligence."""
    import math, random
    W, H = 1200, 600
    dark = theme == "dark"
    ink = "#ffffff" if dark else "#1d1d1f"
    base = ("#06070c", "#0d1020") if dark else ("#eef1f8", "#f8f4f6")
    rnd = random.Random(7)

    # ── backdrop (everything here is also refracted through the glass) ──
    blobs = [("#0a84ff", 160, 470, 250), ("#5e5ce6", 420, 560, 230), ("#bf5af2", 640, 450, 240),
             ("#ff375f", 880, 560, 230), ("#ff9f0a", 1080, 440, 220), ("#64d2ff", 300, 120, 170), ("#ff6ad5", 960, 110, 160)]
    op = 0.72 if dark else 0.55
    bg = (f'<rect width="{W}" height="{H}" fill="url(#base)"/>'
          '<g filter="url(#soft)">'
          + "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{c}" opacity="{op}" class="b{i % 4}"/>' for i, (c, x, y, r) in enumerate(blobs))
          + '</g>')
    line = ink
    lo = 0.16 if dark else 0.14
    # circuit traces (left): orthogonal runs with 45° jogs, ending in vias
    traces = ""
    for i in range(16):
        y0 = 70 + i * 32 + rnd.randint(-6, 6)
        x0 = 0
        x1 = rnd.randint(120, 330)
        dy = rnd.choice([-32, 0, 32])
        x2 = x1 + abs(dy) if dy else x1
        x3 = x2 + rnd.randint(30, 170)
        traces += (f'<path d="M{x0} {y0}H{x1}L{x2} {y0 + dy}H{x3}" fill="none" stroke="{line}" stroke-width="1.6" stroke-linecap="round"/>'
                   f'<circle cx="{x3}" cy="{y0 + dy}" r="4.5" fill="none" stroke="{line}" stroke-width="1.6"/>')
    # neural net (right): layered nodes with curved synapses
    cols = [(800, 5), (920, 7), (1040, 6), (1150, 4)]
    nodes = [[(x, 300 + (j - (n - 1) / 2) * 62) for j in range(n)] for x, n in cols]
    net = ""
    for a, b in zip(nodes, nodes[1:]):
        for (x1, y1) in a:
            for (x2, y2) in b:
                if rnd.random() < 0.55:
                    mx = (x1 + x2) / 2
                    net += f'<path d="M{x1} {y1:.0f}C{mx} {y1:.0f} {mx} {y2:.0f} {x2} {y2:.0f}" fill="none" stroke="{line}" stroke-width="1.1"/>'
    for layer in nodes:
        for (x, y) in layer:
            net += f'<circle cx="{x}" cy="{y:.0f}" r="5" fill="{line}"/>'
    bg += (f'<g mask="url(#fadeL)" opacity="{lo}">{traces}</g>'
           f'<g mask="url(#fadeR)" opacity="{lo}">{net}</g>')

    # the flow line that runs through every glass tile
    xs = [190, 395, 600, 805, 1010]
    cy = 452
    pts = [(40, cy)] + [(x, cy) for x in xs] + [(1160, cy)]
    d = f"M{pts[0][0]} {pts[0][1]}"
    for k, ((x1, y1), (x2, y2)) in enumerate(zip(pts, pts[1:])):
        amp = 34 if k % 2 == 0 else -34
        d += f"C{x1 + (x2 - x1) * .4} {y1 + amp} {x1 + (x2 - x1) * .6} {y2 + amp} {x2} {y2}"
    bg += (f'<path d="{d}" fill="none" stroke="url(#spec)" stroke-width="3" stroke-linecap="round" opacity=".9"/>'
           f'<path d="{d}" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round" stroke-dasharray="2 22" class="flow" opacity="{.9 if dark else .8}"/>'
           f'<circle r="7" fill="#fff" filter="url(#glowF)"><animateMotion dur="7s" repeatCount="indefinite" path="{d}"/></circle>'
           f'<circle r="5" fill="#fff" opacity=".7" filter="url(#glowF)"><animateMotion dur="7s" begin="-3.5s" repeatCount="indefinite" path="{d}"/></circle>')

    # ── glass ──
    S, R = 104, 30
    tiles = [("chip", "Silicon", "#0a84ff"), ("code", "Firmware", "#5e5ce6"), ("plane", "Avionics", "#bf5af2"),
             ("hammer", "Tools", "#ff375f"), ("sparkles", "Intelligence", "#ff9f0a")]
    rects = [(x - S / 2, cy - S / 2) for x in xs]
    clip = "".join(f'<rect x="{x}" y="{y}" width="{S}" height="{S}" rx="{R}"/>' for x, y in rects)
    # big glass card behind the headline
    gx, gy, gw, gh, gr = 170, 96, 860, 248, 44
    clip_card = f'<rect x="{gx}" y="{gy}" width="{gw}" height="{gh}" rx="{gr}"/>'

    defs = (
        f'<linearGradient id="base" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{base[0]}"/><stop offset="1" stop-color="{base[1]}"/></linearGradient>'
        + spectrum_gradient("spec")
        + '<filter id="soft" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="60"/></filter>'
        '<filter id="glowF" x="-200%" y="-200%" width="500%" height="500%"><feGaussianBlur stdDeviation="3" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
        # refraction: displace + soften + boost saturation, the "liquid" in liquid glass
        '<filter id="refract" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB">'
        '<feTurbulence type="fractalNoise" baseFrequency="0.006 0.012" numOctaves="2" seed="11" result="n"/>'
        '<feDisplacementMap in="SourceGraphic" in2="n" scale="70" xChannelSelector="R" yChannelSelector="G" result="d"/>'
        '<feGaussianBlur in="d" stdDeviation="5" result="bl"/>'
        f'<feColorMatrix in="bl" type="saturate" values="{1.3 if dark else 1.5}"/></filter>'
        '<filter id="frost" x="0" y="0" width="100%" height="100%" color-interpolation-filters="sRGB">'
        '<feGaussianBlur stdDeviation="22" result="bl"/>'
        f'<feColorMatrix in="bl" type="saturate" values="{1.0 if dark else 1.3}"/></filter>'
        f'<filter id="gshadow" x="-30%" y="-30%" width="160%" height="180%"><feDropShadow dx="0" dy="14" stdDeviation="16" flood-color="#000" flood-opacity="{.45 if dark else .14}"/></filter>'
        f'<clipPath id="glassClip">{clip}</clipPath><clipPath id="cardClip">{clip_card}</clipPath>'
        f'<clipPath id="frame"><rect x="0" y="0" width="{W}" height="{H}" rx="40"/></clipPath>'
        # specular rim: bright top-left, dim middle, soft bounce bottom-right
        '<linearGradient id="rim" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="#fff" stop-opacity="{.95 if dark else 1}"/><stop offset=".35" stop-color="#fff" stop-opacity=".12"/>'
        f'<stop offset=".7" stop-color="#fff" stop-opacity=".08"/><stop offset="1" stop-color="#fff" stop-opacity="{.6 if dark else .9}"/></linearGradient>'
        '<linearGradient id="sheen" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="#fff" stop-opacity="{.22 if dark else .55}"/><stop offset=".45" stop-color="#fff" stop-opacity="0"/></linearGradient>'
        '<linearGradient id="fadeLg" x1="0" x2="1"><stop offset="0" stop-color="#fff"/><stop offset=".42" stop-color="#fff" stop-opacity="0"/></linearGradient>'
        '<linearGradient id="fadeRg" x1="0" x2="1"><stop offset=".6" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#fff"/></linearGradient>'
        f'<mask id="fadeL"><rect width="{W}" height="{H}" fill="url(#fadeLg)"/></mask>'
        f'<mask id="fadeR"><rect width="{W}" height="{H}" fill="url(#fadeRg)"/></mask>'
        f'<g id="bg">{bg}</g>'
    )

    tint = "#ffffff"
    tint_op = .07 if dark else .32
    body = '<g clip-path="url(#frame)"><use href="#bg"/>'
    # headline glass card
    body += (f'<rect x="{gx}" y="{gy}" width="{gw}" height="{gh}" rx="{gr}" fill="{base[0]}" filter="url(#gshadow)" opacity=".5"/>'
             f'<g clip-path="url(#cardClip)"><use href="#bg" filter="url(#frost)"/></g>'
             f'<rect x="{gx}" y="{gy}" width="{gw}" height="{gh}" rx="{gr}" fill="{"#000" if dark else tint}" fill-opacity="{.38 if dark else .38}"/>'
             f'<rect x="{gx}" y="{gy}" width="{gw}" height="{gh}" rx="{gr}" fill="url(#sheen)"/>'
             f'<rect x="{gx + .75}" y="{gy + .75}" width="{gw - 1.5}" height="{gh - 1.5}" rx="{gr}" fill="none" stroke="url(#rim)" stroke-width="1.5"/>')
    # tiles: shadow, refracted backdrop, tint, sheen, rim, glyph, label
    for (x, y) in rects:
        body += f'<rect x="{x}" y="{y}" width="{S}" height="{S}" rx="{R}" fill="{base[0]}" opacity=".6" filter="url(#gshadow)"/>'
    body += '<g clip-path="url(#glassClip)"><use href="#bg" filter="url(#refract)"/></g>'
    for (x, y), (ic, label, c) in zip(rects, tiles):
        body += (f'<rect x="{x}" y="{y}" width="{S}" height="{S}" rx="{R}" fill="{"#000" if dark else tint}" fill-opacity="{.22 if dark else tint_op}"/>'
                 f'<rect x="{x}" y="{y}" width="{S}" height="{S}" rx="{R}" fill="{c}" fill-opacity="{.16 if dark else .06}"/>'
                 f'<rect x="{x}" y="{y}" width="{S}" height="{S}" rx="{R}" fill="url(#sheen)"/>'
                 f'<rect x="{x + .75}" y="{y + .75}" width="{S - 1.5}" height="{S - 1.5}" rx="{R}" fill="none" stroke="url(#rim)" stroke-width="1.5"/>'
                 f'<g transform="translate({x + S / 2 - 22},{y + S / 2 - 22}) scale(1.375)" fill="{ink}" color="{ink}">{ICONS[ic]}</g>'
                 f'<text x="{x + S / 2}" y="{y + S + 34}" text-anchor="middle" font-size="16" font-weight="600" letter-spacing="-0.1" fill="{ink}" fill-opacity="{.92 if dark else .85}">{label}</text>')
    # headline
    sub = "#ebebf5" if dark else "#3a3a3c"
    body += (f'<text x="600" y="{gy + 58}" text-anchor="middle" font-size="15" font-weight="600" letter-spacing="2.6" fill="{sub}" fill-opacity=".8">CTO · FLYVI TECHNOLOGIES</text>'
             f'<text x="600" y="{gy + 146}" text-anchor="middle" font-size="84" font-weight="700" letter-spacing="-3" fill="{ink}">Hithesh Karanth</text>'
             f'<text x="600" y="{gy + 198}" text-anchor="middle" font-size="26" font-weight="500" letter-spacing="-0.4" fill="{sub}">From silicon to intelligence, built to be verified.</text>')
    # window controls, floating in the frame corner
    body += ('<circle cx="40" cy="38" r="7" fill="#ff5f57"/><circle cx="64" cy="38" r="7" fill="#febc2e"/><circle cx="88" cy="38" r="7" fill="#28c840"/>')
    body += '</g>'
    body += f'<rect x=".75" y=".75" width="{W - 1.5}" height="{H - 1.5}" rx="40" fill="none" stroke="{ink}" stroke-opacity="{.14 if dark else .08}" stroke-width="1.5"/>'

    style = (
        "@keyframes d0{50%{transform:translate(90px,-50px)}}@keyframes d1{50%{transform:translate(-80px,-60px)}}"
        "@keyframes d2{50%{transform:translate(70px,40px)}}@keyframes d3{50%{transform:translate(-100px,-30px)}}"
        ".b0{animation:d0 16s ease-in-out infinite}.b1{animation:d1 19s ease-in-out infinite}"
        ".b2{animation:d2 17s ease-in-out infinite}.b3{animation:d3 21s ease-in-out infinite}"
        "@keyframes flow{to{stroke-dashoffset:-240}}.flow{animation:flow 6s linear infinite}"
        "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"
    )
    return svg(W, H, body, defs, style)


ICONS = {  # simple SF Symbol-ish glyphs drawn in a 32×32 box
    "plane": '<path d="M16 3c1.4 0 2.2 1.4 2.2 3v6.6l10.3 6.1v3l-10.3-3.2v5.7l3.3 2.5V29L16 27.6 10.5 29v-2.3l3.3-2.5v-5.7L3.5 21.7v-3l10.3-6.1V6c0-1.6.8-3 2.2-3z"/>',
    "chip": '<rect x="8" y="8" width="16" height="16" rx="3"/><rect x="12.5" y="12.5" width="7" height="7" rx="1.2" fill-opacity=".35" fill="#fff"/>'
            + "".join(f'<rect x="{x}" y="3" width="2.2" height="5" rx="1"/><rect x="{x}" y="24" width="2.2" height="5" rx="1"/>'
                      f'<rect x="3" y="{x}" width="5" height="2.2" rx="1"/><rect x="24" y="{x}" width="5" height="2.2" rx="1"/>' for x in (11, 15, 19)),
    "hammer": '<path d="M5 9.5 14.5 3l4 3.2-2.6 2.3 2 2 9.6 12.4-3.6 3.6L11.5 16.9l-2-2-2.4 2.6L4 13.6z"/>',
    "sparkles": '<path d="M13 3l2.4 6.6L22 12l-6.6 2.4L13 21l-2.4-6.6L4 12l6.6-2.4z"/><path d="M24 17l1.3 3.7L29 22l-3.7 1.3L24 27l-1.3-3.7L19 22l3.7-1.3z"/>',
    "code": '<g fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M10 9 3.5 16 10 23M22 9l6.5 7-6.5 7M18.5 6l-5 20"/></g>',
    "bolt": '<path d="M18.5 2 6 18h8.2L12 30l14-17.5h-8.3z"/>',
}


def bento(t, theme):
    W, H = 1200, 470
    tiles = [
        # x, y, w, h, icon, color, title, lines
        (16, 12, 576, 214, "plane", "#0a84ff", "Aerospace & Defence",
         ["Avionics data loading, high-reliability control", "and safety-critical firmware for aircraft systems."]),
        (608, 12, 280, 214, "chip", "#30d158", "Embedded", ["STM32 · ESP32", "Embedded Linux HMI"]),
        (904, 12, 280, 214, "hammer", "#ff9f0a", "Developer Tools", ["AI-native IDEs,", "verification, traceability"]),
        (16, 242, 384, 214, "sparkles", "#bf5af2", "Applied AI", ["Voice assistants, research", "agents, knowledge graphs"]),
        (416, 242, 768, 214, "bolt", "#76b900", "MLOps & Inference",
         ["Serving 35B MoE models on a single NVIDIA DGX Spark.", "vLLM · NVFP4 / FP8 quantization · speculative decoding"]),
    ]
    defs = shadow_filter(t, "shadow", 8, 14)
    body = ""
    for i, (x, y, w, h, ic, c, title, lines) in enumerate(tiles):
        defs += (f'<radialGradient id="g{i}" cx="100%" cy="0%" r="90%"><stop offset="0" stop-color="{c}" stop-opacity="{t["glow"]}"/>'
                 f'<stop offset="1" stop-color="{c}" stop-opacity="0"/></radialGradient>')
        body += (f'<g class="t{i}"><g filter="url(#shadow)"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="28" fill="{t["card"]}"/></g>'
                 f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="28" fill="url(#g{i})"/>'
                 f'<rect x="{x + .5}" y="{y + .5}" width="{w - 1}" height="{h - 1}" rx="28" fill="none" stroke="{t["line"]}"/>'
                 f'<rect x="{x + 28}" y="{y + 28}" width="52" height="52" rx="13" fill="{c}"/>'
                 f'<g transform="translate({x + 38},{y + 38}) scale(1)" fill="#fff">{ICONS[ic]}</g>'
                 f'<text x="{x + 28}" y="{y + 126}" font-size="26" font-weight="700" letter-spacing="-0.5" fill="{t["text"]}">{escape(title)}</text>')
        for j, line in enumerate(lines):
            body += f'<text x="{x + 28}" y="{y + 156 + j * 24}" font-size="17" fill="{t["sub"]}">{escape(line)}</text>'
        body += "</g>"
    return svg(W, H, body, defs)


def heading(t, title, sub, theme):
    """Apple product-page style headline: bold statement + grey continuation."""
    W, H = 1200, 132
    body = (f'<text x="16" y="72" font-size="50" font-weight="700" letter-spacing="-1.6" fill="{t["text"]}">{escape(title)}'
            f'<tspan fill="{t["faint"]}"> {escape(sub)}</tspan></text>'
            f'<rect x="16" y="98" width="64" height="5" rx="2.5" fill="url(#bar)"/>')
    return svg(W, H, body, spectrum_gradient("bar"))


def inference(t, theme):
    W, H = 1200, 400
    green = "#76b900"
    defs = shadow_filter(t, "shadow", 8, 14) + (
        f'<linearGradient id="num" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#9be15d"/><stop offset="1" stop-color="{green}"/></linearGradient>')
    body = (f'<g filter="url(#shadow)"><rect x="16" y="12" width="1168" height="364" rx="30" fill="{t["card"]}"/></g>'
            f'<rect x="16.5" y="12.5" width="1167" height="363" rx="30" fill="none" stroke="{t["line"]}"/>'
            f'<text x="56" y="66" font-size="14" font-weight="600" letter-spacing="1.4" fill="{green}">NVIDIA DGX SPARK · GB10 · 128 GB UNIFIED MEMORY</text>'
            f'<text x="56" y="106" font-size="32" font-weight="700" letter-spacing="-0.8" fill="{t["text"]}">Frontier-class MoE. One desk-side box.</text>'
            f'<text x="56" y="136" font-size="17" fill="{t["sub"]}">262K context on every model. Every number measured on the live deployment.</text>')
    cols = [("Ornith-1.5", "351.7", "tok/s · 16 users", "NVFP4 + FP8 + MTP · vision", True),
            ("Qwen3.8 Distill", "373", "tok/s · 16 users", "Self-quantized, data-free", False),
            ("Qwen3.6", "219", "tok/s peak", "12 users · 5.1× prefix cache", False)]
    for i, (name, num, unit, note, live) in enumerate(cols):
        x = 56 + i * 376
        if i:
            body += f'<line x1="{x - 24}" y1="176" x2="{x - 24}" y2="336" stroke="{t["line"]}"/>'
        body += f'<text x="{x}" y="190" font-size="19" font-weight="600" fill="{t["text"]}">{name}</text>'
        if live:
            body += (f'<circle cx="{x + 118}" cy="184" r="4.5" fill="#30d158" class="pulse"/>'
                     f'<text x="{x + 128}" y="189" font-size="12" font-weight="700" letter-spacing="1" fill="#30d158">LIVE</text>')
        body += (f'<text x="{x}" y="270" font-size="72" font-weight="800" letter-spacing="-2.5" fill="url(#num)">{num}</text>'
                 f'<text x="{x}" y="300" font-size="16" font-weight="500" fill="{t["sub"]}">{unit}</text>'
                 f'<text x="{x}" y="330" font-size="14" fill="{t["faint"]}">{note}</text>')
    style = "@keyframes pulse{0%,100%{opacity:1}50%{opacity:.25}}.pulse{animation:pulse 1.8s ease-in-out infinite}"
    return svg(W, H, body, defs, style)


def stack(t, theme):
    W = 1200
    layers = [  # top (intelligence) to bottom (silicon)
        ("Intelligence", "#ff9f0a", ["vLLM", "NVFP4 / FP8", "Speculative decoding", "Voice AI", "Agents", "Claude · Gemini · Codex"]),
        ("Tools", "#ff375f", ["TypeScript", "React", "Tauri", "Code-OSS", "FastAPI", "PySide6"]),
        ("Assurance", "#bf5af2", ["DO-178C", "MISRA", "CBMC", "CodeQL", "MC/DC", "Traceability"]),
        ("Systems", "#5e5ce6", ["C++23", "Rust", "Qt 6", "Embedded Linux", "VxWorks", "ARINC 615A / 665"]),
        ("Silicon", "#0a84ff", ["C", "STM32", "ESP32", "LVGL", "CAN · UART · USB", "Sensor telemetry"]),
    ]
    row, gap, top = 76, 12, 12
    H = top + len(layers) * (row + gap) + 16
    defs = shadow_filter(t, "shadow", 6, 12)
    body = ""
    for i, (name, c, items) in enumerate(layers):
        y = top + i * (row + gap)
        defs += (f'<linearGradient id="l{i}" x1="0" x2="1"><stop offset="0" stop-color="{c}" stop-opacity="{t["glow"]}"/>'
                 f'<stop offset=".45" stop-color="{c}" stop-opacity="0"/></linearGradient>')
        body += (f'<g filter="url(#shadow)"><rect x="16" y="{y}" width="{W - 32}" height="{row}" rx="22" fill="{t["card"]}"/></g>'
                 f'<rect x="16" y="{y}" width="{W - 32}" height="{row}" rx="22" fill="url(#l{i})"/>'
                 f'<rect x="16.5" y="{y + .5}" width="{W - 33}" height="{row - 1}" rx="22" fill="none" stroke="{t["line"]}"/>'
                 f'<circle cx="52" cy="{y + row / 2}" r="7" fill="{c}"/>'
                 f'<text x="72" y="{y + row / 2 + 7}" font-size="20" font-weight="700" letter-spacing="-0.3" fill="{t["text"]}">{name}</text>')
        x = 250
        for it in items:
            w = int(len(it) * 15 * 0.56) + 28
            body += (f'<rect x="{x}" y="{y + row / 2 - 17}" width="{w}" height="34" rx="17" fill="{t["bg"]}" stroke="{t["line"]}"/>'
                     f'<text x="{x + w / 2}" y="{y + row / 2 + 5}" text-anchor="middle" font-size="15" font-weight="500" fill="{t["sub"]}">{escape(it)}</text>')
            x += w + 10
    return svg(W, H, body, defs)


def dock_icon(t, kind):
    S = 96
    g = {
        "github": ("#24292f", '<path fill="#fff" transform="translate(24,24) scale(3)" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>'),
        "x": ("#000000", '<path fill="#fff" transform="translate(26,26) scale(1.85)" d="M18.9 1.2h3.7l-8 9.2 9.4 12.4h-7.4l-5.8-7.6-6.6 7.6H.5l8.6-9.8L0 1.2h7.6l5.2 6.9zm-1.3 19.4h2L6.5 3.2H4.3z"/>'),
        "web": ("#0071e3", '<g fill="none" stroke="#fff" stroke-width="4"><circle cx="48" cy="48" r="22"/><ellipse cx="48" cy="48" rx="10" ry="22"/><path d="M26 48h44M30 37h36M30 59h36"/></g>'),
        "repos": ("#ff9f0a", '<g fill="#fff"><rect x="26" y="30" width="44" height="40" rx="6" fill-opacity=".55"/><rect x="26" y="24" width="20" height="12" rx="4"/><rect x="26" y="34" width="44" height="36" rx="6"/></g>'),
    }[kind]
    defs = (f'<linearGradient id="sheen" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".22"/>'
            f'<stop offset=".5" stop-color="#fff" stop-opacity="0"/></linearGradient>')
    body = (f'<rect x="4" y="4" width="{S - 8}" height="{S - 8}" rx="21" fill="{g[0]}"/>{g[1]}'
            f'<rect x="4" y="4" width="{S - 8}" height="{S - 8}" rx="21" fill="url(#sheen)"/>'
            f'<rect x="4.5" y="4.5" width="{S - 9}" height="{S - 9}" rx="21" fill="none" stroke="{t["chrome_line"]}" stroke-opacity=".6"/>')
    return svg(S, S, body, defs)


def footer(t, theme):
    W, H = 1200, 90
    body = (f'<text x="600" y="40" text-anchor="middle" font-size="15" fill="{t["faint"]}">Thanks for stopping by. Built in the open.</text>'
            f'<rect x="568" y="60" width="64" height="5" rx="2.5" fill="url(#bar)"/>')
    return svg(W, H, body, spectrum_gradient("bar"))

# ── main ─────────────────────────────────────────────────────────────────────

WIDE = {"noyce", "wirevoice", "openterminalui", "arinc", "ornith"}
HEADINGS = {
    "now": ("Building now.", "Firmware you can prove."),
    "award": ("Recognition.", "Shipped under a deadline."),
    "oss": ("Open source.", "Yours to run."),
    "systems": ("Systems work.", "Close to the metal."),
    "mlops": ("Inference.", "Self-hosted, measured."),
    "about": ("What I do.", "Across the stack."),
    "stack": ("Stack.", "Every layer, hands-on."),
    "stars": ("Momentum.", "Stars over time."),
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    counts = stars()
    for theme, t in THEMES.items():
        files = {
            f"hero-{theme}.svg": hero(t, theme),
            f"bento-{theme}.svg": bento(t, theme),
            f"inference-{theme}.svg": inference(t, theme),
            f"stack-{theme}.svg": stack(t, theme),
            f"footer-{theme}.svg": footer(t, theme),
        }
        for k, p in PROJECTS.items():
            files[f"card-{k}-{theme}.svg"] = card(k, p, t, theme, counts, k in WIDE)
        for k, (a, b) in HEADINGS.items():
            files[f"h-{k}-{theme}.svg"] = heading(t, a, b, theme)
        for k in ("github", "x", "web", "repos"):
            files[f"dock-{k}-{theme}.svg"] = dock_icon(t, k)
        for name, content in files.items():
            (OUT / name).write_text(content)
    print(f"wrote {len(list(OUT.glob('*.svg')))} files to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
