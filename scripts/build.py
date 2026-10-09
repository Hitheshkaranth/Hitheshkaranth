#!/usr/bin/env python3
"""Render the profile's SVG artwork (light + dark) into assets/gen/.

Design language: shadcn/ui components (zinc neutrals, 1px borders, badges,
outline buttons, Lucide icons) with Apple type, spacing and window chrome.

Run locally or from the daily workflow:  python3 scripts/build.py
Star counts are fetched from the GitHub API (GITHUB_TOKEN optional) and cached
in scripts/stars.json so the build still works offline.
"""
import base64, hashlib, io, json, os, re, textwrap, urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
OUT = ASSETS / "gen"
OWNER = "Hitheshkaranth"
FONT = "-apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Geist', 'Inter', 'Segoe UI', Helvetica, Arial, sans-serif"

THEMES = {  # shadcn/ui zinc tokens
    "light": dict(card="#ffffff", fg="#09090b", muted="#f4f4f5", muted_fg="#71717a", border="#e4e4e7",
                  primary="#18181b", primary_fg="#fafafa", dot="#d4d4d8", shadow="0.06",
                  live_bg="#dcfce7", live_fg="#15803d"),
    "dark":  dict(card="#09090b", fg="#fafafa", muted="#27272a", muted_fg="#a1a1aa", border="#27272a",
                  primary="#fafafa", primary_fg="#18181b", dot="#27272a", shadow="0.5",
                  live_bg="#052e16", live_fg="#4ade80"),
}

# ── data ─────────────────────────────────────────────────────────────────────

PROJECTS = {
    "noyce": dict(repo="noyce-ide-dist", logo="noyce-ide.png", accent="#40c8e0",
        eyebrow="Building now", title="Noyce IDE",
        tagline="Firmware you can prove.",
        desc="An AI-native Code-OSS workbench for safety-critical firmware. Requirements, source, tests, "
             "traceability, MISRA, CBMC, CodeQL, measured MC/DC and hardware tooling in one window.",
        meta="DO-178C evidence · Code-OSS · TypeScript", award="Stanford × DeepMind Hackathon", stars=False),
    "wirevoice": dict(repo=None, logo="wirevoice.png", accent="#ff9f0a",
        eyebrow="Recognition", title="WireVoice",
        tagline="Ask the schematic. In your language.",
        desc="A voice-first assistant for technicians on complex wiring harness drawings. It names the "
             "terminal, the wire gauge and the exact sheet it came from, across eleven Indian languages.",
        meta="Voice AI · Sarvam · Python", award="Winner · Sarvam Epoch Buildathon 2026", stars=False),
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
    "eds": dict(repo="EmbeddedDisplayStudio", logo="embedded-display-studio.png", accent="#32ade6",
        eyebrow="Open source", title="EmbeddedDisplayStudio",
        desc="Describe, draw or bring an HMI and ship it to embedded Linux panels. AI design, a C + LVGL "
             "runtime, and atomic SSH deploys with automatic rollback.",
        meta="Python · LVGL · Embedded Linux", badge="MIT", award="Berkeley × DeepMind Hackathon"),
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


def tw(text, size, weight=400):
    """Rough rendered width of `text` in the system UI font."""
    return len(text) * size * (0.55 if weight >= 600 else 0.5)


def svg(w, h, body, defs="", style=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{w}" height="{h}" viewBox="0 0 {w} {h}" font-family="{FONT}">'
            f'<style>{style}</style><defs>{defs}</defs>{body}</svg>\n')


def shadow_sm(t, fid="sm"):
    return (f'<filter id="{fid}" x="-10%" y="-10%" width="120%" height="140%">'
            f'<feDropShadow dx="0" dy="1" stdDeviation="1.5" flood-color="#000" flood-opacity="{t["shadow"]}"/></filter>')


# Lucide icons (ISC licensed), drawn in a 24×24 box with 2px strokes
LUCIDE = {
    "search": '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    "cpu": '<rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6" rx="1"/>'
           '<path d="M15 2v2M15 20v2M2 15h2M2 9h2M20 15h2M20 9h2M9 2v2M9 20v2"/>',
    "code": '<path d="m16 18 6-6-6-6M8 6l-6 6 6 6"/>',
    "plane": '<path d="M17.8 19.2 16 11l3.5-3.5C21 6 21.5 4 21 3c-1-.5-3 0-4.5 1.5L13 8 4.8 6.2c-.5-.1-.9.1-1.1.5l-.3.5c-.2.5-.1 1 .3 1.3L9 12l-2 3H4l-1 1 3 2 2 3 1-1v-3l3-2 3.5 5.3c.3.4.8.5 1.3.3l.5-.2c.4-.3.6-.7.5-1.2z"/>',
    "shield": '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/>',
    "wrench": '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>',
    "sparkles": '<path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z"/><path d="M20 3v4M22 5h-4"/>',
    "zap": '<path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z"/>',
    "star": '<path d="M11.525 2.295a.53.53 0 0 1 .95 0l2.31 4.679a2.123 2.123 0 0 0 1.595 1.16l5.166.756a.53.53 0 0 1 .294.904l-3.736 3.638a2.123 2.123 0 0 0-.611 1.878l.882 5.14a.53.53 0 0 1-.771.56l-4.618-2.428a2.122 2.122 0 0 0-1.973 0L6.396 21.01a.53.53 0 0 1-.77-.56l.881-5.139a2.122 2.122 0 0 0-.611-1.879L2.16 9.795a.53.53 0 0 1 .294-.906l5.165-.755a2.122 2.122 0 0 0 1.597-1.16z"/>',
    "arrow": '<path d="M5 12h14M12 5l7 7-7 7"/>',
    "chevron": '<path d="m9 18 6-6-6-6"/>',
    "globe": '<circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20M2 12h20"/>',
    "folder": '<path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/>',
    "award": '<circle cx="12" cy="8" r="6"/><path d="M15.477 12.89 17 22l-5-3-5 3 1.523-9.11"/>',
}
BRANDS = {  # filled marks, 24×24
    "github": '<path transform="scale(1.5)" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>',
    "x": '<path d="M18.9 1.2h3.7l-8 9.2 9.4 12.4h-7.4l-5.8-7.6-6.6 7.6H.5l8.6-9.8L0 1.2h7.6l5.2 6.9zm-1.3 19.4h2L6.5 3.2H4.3z"/>',
}


def icon(name, x, y, size, color, sw=2):
    s = size / 24
    if name in BRANDS:
        return f'<g transform="translate({x},{y}) scale({s})" fill="{color}">{BRANDS[name]}</g>'
    return (f'<g transform="translate({x},{y}) scale({s})" fill="none" stroke="{color}" stroke-width="{sw}" '
            f'stroke-linecap="round" stroke-linejoin="round">{LUCIDE[name]}</g>')


def badge(t, x, y, text, variant="secondary", lead=None):
    """shadcn <Badge>: 22px pill, 12px semibold. Returns (width, svg)."""
    pad = 10
    lw = 16 if lead else 0
    w = tw(text, 12, 600) + 2 * pad + lw
    fill, stroke, fg = {"secondary": (t["muted"], "none", t["fg"]),
                        "outline": ("none", t["border"], t["fg"]),
                        "default": (t["primary"], "none", t["primary_fg"])}[variant]
    out = f'<rect x="{x}" y="{y}" width="{w:.0f}" height="22" rx="11" fill="{fill}" stroke="{stroke}"/>'
    if lead:
        out += icon(lead, x + pad - 1, y + 5, 12, fg, 2.4)
    out += f'<text x="{x + pad + lw:.0f}" y="{y + 15}" font-size="12" font-weight="600" fill="{fg}">{escape(text)}</text>'
    return w, out


def button(t, x, y, label, variant="outline", lead=None, trail=None, h=36):
    """shadcn <Button size=default>. Returns (width, svg)."""
    pad, gap = 16, 8
    w = tw(label, 14, 500) * 1.08 + 2 * pad + (16 + gap if lead else 0) + (16 + gap if trail else 0)
    fill, stroke, fg = {"outline": (t["card"], t["border"], t["fg"]),
                        "default": (t["primary"], "none", t["primary_fg"]),
                        "secondary": (t["muted"], "none", t["fg"])}[variant]
    out = f'<rect x="{x}" y="{y}" width="{w:.0f}" height="{h}" rx="8" fill="{fill}" stroke="{stroke}"/>'
    cx = x + pad
    if lead:
        out += icon(lead, cx, y + (h - 16) / 2, 16, fg)
        cx += 16 + gap
    out += f'<text x="{cx:.0f}" y="{y + h / 2 + 5}" font-size="14" font-weight="500" fill="{fg}">{escape(label)}</text>'
    if trail:
        out += icon(trail, x + w - pad - 16, y + (h - 16) / 2, 16, fg)
    return w, out


def logo_box(p, t, x, y, s):
    """Project logo in a bordered, rounded square (shadcn Avatar, Apple corner radius)."""
    r = s * 0.24
    cid = f"lb{x}{y}"
    defs = f'<clipPath id="{cid}"><rect x="{x}" y="{y}" width="{s}" height="{s}" rx="{r}"/></clipPath>'
    if p.get("photo"):
        img = f'<image x="{x}" y="{y}" width="{s}" height="{s}" href="{data_uri(p["logo"], 192, True)}" clip-path="url(#{cid})" preserveAspectRatio="xMidYMid slice"/>'
        fill = t["muted"]
    elif p.get("wide_logo"):
        pad = s * 0.1
        img = f'<image x="{x + pad}" y="{y}" width="{s - 2 * pad}" height="{s}" href="{data_uri(p["logo"], 192)}" preserveAspectRatio="xMidYMid meet"/>'
        fill = "#ffffff"
    else:
        pad = s * 0.16
        img = f'<image x="{x + pad}" y="{y + pad}" width="{s - 2 * pad}" height="{s - 2 * pad}" href="{data_uri(p["logo"], 192)}" preserveAspectRatio="xMidYMid meet"/>'
        fill = t["muted"]
    return defs, (f'<rect x="{x}" y="{y}" width="{s}" height="{s}" rx="{r}" fill="{fill}"/>{img}'
                  f'<rect x="{x + .5}" y="{y + .5}" width="{s - 1}" height="{s - 1}" rx="{r}" fill="none" stroke="{t["border"]}"/>')


def frame(t, W, H, r=14):
    """shadcn <Card>: 1px border, soft shadow, generous radius."""
    return (f'<rect x="8" y="8" width="{W - 16}" height="{H - 16}" rx="{r}" fill="{t["card"]}" stroke="{t["border"]}" filter="url(#sm)"/>')

# ── artwork ──────────────────────────────────────────────────────────────────

def card(key, p, t, theme, star_counts, wide):
    W, H = (1200, 270) if wide else (600, 290)
    defs = shadow_sm(t)
    body = frame(t, W, H)
    ls = 64 if wide else 48
    d, lb = logo_box(p, t, 32, 32, ls)
    defs += d
    body += lb
    tx = 32 + ls + 18

    # title row (+ inline eyebrow badge on wide cards)
    ts = 26 if wide else 20
    ty = 32 + (30 if wide else 22)
    body += f'<text x="{tx}" y="{ty}" font-size="{ts}" font-weight="600" letter-spacing="-0.5" fill="{t["fg"]}">{escape(p["title"])}</text>'
    if wide:
        _, b = badge(t, tx + tw(p["title"], ts, 600) + 12, ty - 18, p["eyebrow"], "secondary")
        body += b
        sub = p.get("tagline") or ""
    else:
        sub = p["eyebrow"]
    body += f'<text x="{tx}" y="{ty + (28 if wide else 22)}" font-size="{16 if wide else 14}" fill="{t["muted_fg"]}">{escape(sub)}</text>'
    if p.get("award") and not wide:  # no room top-right on half-width cards: sit beside the subtitle
        body += badge(t, tx + tw(sub, 14) + 10, ty + 6, p["award"], "default", lead="award")[1]

    # top-right badges
    bx = W - 32
    if p.get("repo") and p.get("stars") is not False and star_counts.get(p["repo"], 0) >= 5:
        txt = f'{star_counts[p["repo"]]:,}'
        w = tw(txt, 12, 600) + 36
        bx -= w
        body += badge(t, bx, 34, txt, "outline", lead="star")[1]
        bx -= 8
    if p.get("badge"):
        w, _ = badge(t, 0, 0, p["badge"], "secondary")
        bx -= w
        body += badge(t, bx, 34, p["badge"], "secondary")[1]
        bx -= 8
    if p.get("award") and wide:
        w, _ = badge(t, 0, 0, p["award"], "default", lead="award")
        bx -= w
        body += badge(t, bx, 34, p["award"], "default", lead="award")[1]

    # description
    y = 134 if wide else 118
    for line in wrap(p["desc"], 128 if wide else 72):
        body += f'<text x="{32 if not wide else tx}" y="{y}" font-size="15" fill="{t["muted_fg"]}">{escape(line)}</text>'
        y += 24

    # footer: separator, tech badges, action
    sy = H - 76
    body += f'<line x1="9" y1="{sy}" x2="{W - 9}" y2="{sy}" stroke="{t["border"]}"/>'
    bx = 32
    for tech in [s.strip() for s in p["meta"].split("·")]:
        w, b = badge(t, bx, sy + 23, tech, "outline")
        body += b
        bx += w + 6
    label = "View repository" if p.get("repo") else "Read announcement"
    w, _ = button(t, 0, 0, label, "outline", trail="arrow")
    body += button(t, W - 32 - w, sy + 16, label, "outline", trail="arrow")[1]
    return svg(W, H, body, defs)


def hero(t, theme):
    W, H = 1200, 770
    dark = theme == "dark"
    defs = (
        f'<pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="1.5" cy="1.5" r="1.1" fill="{t["dot"]}"/></pattern>'
        '<radialGradient id="dotsFade" cx="50%" cy="30%" r="62%"><stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>'
        f'<mask id="dotsMask"><rect width="{W}" height="{H}" fill="url(#dotsFade)"/></mask>'
        # spotlight from above the headline (Apple keynote lighting)
        f'<radialGradient id="spot" cx="50%" cy="0%" r="70%" fx="50%" fy="0%"><stop offset="0" stop-color="{"#ffffff" if dark else "#0a84ff"}" stop-opacity="{.13 if dark else .07}"/>'
        f'<stop offset="1" stop-color="{"#ffffff" if dark else "#0a84ff"}" stop-opacity="0"/></radialGradient>'
        f'<radialGradient id="aura" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#0a84ff" stop-opacity="{.26 if dark else .16}"/>'
        f'<stop offset=".6" stop-color="#40c8e0" stop-opacity="{.08 if dark else .05}"/><stop offset="1" stop-color="#40c8e0" stop-opacity="0"/></radialGradient>'
        # headline fades from foreground to muted, like shadcn's hero type
        f'<linearGradient id="ink" gradientUnits="userSpaceOnUse" x1="0" y1="88" x2="0" y2="160"><stop offset="0" stop-color="{t["fg"]}"/>'
        f'<stop offset="1" stop-color="{t["fg"]}" stop-opacity="{.62 if dark else .72}"/></linearGradient>'
        f'<clipPath id="heroClip"><rect x="8" y="8" width="{W - 16}" height="{H - 16}" rx="20"/></clipPath>'
        f'<filter id="win" x="-20%" y="-20%" width="140%" height="160%"><feDropShadow dx="0" dy="28" stdDeviation="32" flood-color="#000" flood-opacity="{.65 if dark else .14}"/></filter>'
        + shadow_sm(t)
    )
    body = (f'<rect x="8" y="8" width="{W - 16}" height="{H - 16}" rx="20" fill="{t["card"]}"/>'
            '<g clip-path="url(#heroClip)">'
            f'<rect width="{W}" height="{H}" fill="url(#dots)" mask="url(#dotsMask)"/>'
            f'<rect width="{W}" height="{H}" fill="url(#spot)"/>'
            f'<ellipse cx="600" cy="500" rx="540" ry="250" fill="url(#aura)" class="aura"/>'
            '</g>'
            f'<rect x="8.5" y="8.5" width="{W - 17}" height="{H - 17}" rx="20" fill="none" stroke="{t["border"]}"/>')

    # headline
    body += (f'<text x="600" y="148" text-anchor="middle" font-size="80" font-weight="700" letter-spacing="-3" fill="url(#ink)">Hithesh Karanth</text>'
             f'<text x="600" y="198" text-anchor="middle" font-size="21" fill="{t["muted_fg"]}">From silicon to intelligence, built to be verified.</text>')

    # macOS window holding a ⌘K command menu
    wx, wy, ww = 250, 250, 700
    rows = [("cpu", "Silicon", "C · STM32 · ESP32 · LVGL"),
            ("code", "Firmware", "CAN · UART · USB · telemetry"),
            ("plane", "Avionics", "ARINC 615A / 665 · VxWorks"),
            ("shield", "Assurance", "DO-178C · MISRA · CBMC · MC/DC"),
            ("wrench", "Tools", "Code-OSS · Tauri · React · Qt 6"),
            ("sparkles", "Intelligence", "vLLM · NVFP4 · agents · voice AI")]
    rh, tb, sb, gl, fb = 46, 40, 54, 34, 42
    wh = tb + sb + gl + len(rows) * rh + 8 + fb
    body += (f'<rect x="{wx}" y="{wy}" width="{ww}" height="{wh}" rx="14" fill="{t["card"]}" filter="url(#win)"/>'
             f'<path d="M{wx + 14} {wy + .5}H{wx + ww - 14}A13.5 13.5 0 0 1 {wx + ww - .5} {wy + 14}V{wy + tb}H{wx + .5}V{wy + 14}A13.5 13.5 0 0 1 {wx + 14} {wy + .5}z" fill="{t["muted"]}" fill-opacity=".45"/>'
             f'<line x1="{wx}" y1="{wy + tb}" x2="{wx + ww}" y2="{wy + tb}" stroke="{t["border"]}"/>'
             f'<circle cx="{wx + 20}" cy="{wy + 20}" r="6" fill="#ff5f57"/><circle cx="{wx + 40}" cy="{wy + 20}" r="6" fill="#febc2e"/><circle cx="{wx + 60}" cy="{wy + 20}" r="6" fill="#28c840"/>'
             f'<text x="{wx + ww / 2}" y="{wy + 25}" text-anchor="middle" font-size="13" font-weight="500" fill="{t["muted_fg"]}">Command Menu</text>')
    sy = wy + tb
    body += (icon("search", wx + 20, sy + 18, 18, t["muted_fg"])
             + f'<rect x="{wx + 50}" y="{sy + 17}" width="1.6" height="20" rx=".8" fill="{t["fg"]}" class="caret"/>'
             f'<text x="{wx + 57}" y="{sy + 32}" font-size="15" fill="{t["muted_fg"]}">Search the stack…</text>'
             f'<rect x="{wx + ww - 60}" y="{sy + 15}" width="40" height="24" rx="6" fill="{t["muted"]}" stroke="{t["border"]}"/>'
             f'<text x="{wx + ww - 40}" y="{sy + 32}" text-anchor="middle" font-size="12" font-weight="600" fill="{t["muted_fg"]}">⌘K</text>'
             f'<line x1="{wx}" y1="{sy + sb}" x2="{wx + ww}" y2="{sy + sb}" stroke="{t["border"]}"/>'
             f'<text x="{wx + 20}" y="{sy + sb + 23}" font-size="12" font-weight="500" fill="{t["muted_fg"]}">Silicon to intelligence</text>')
    ry = sy + sb + gl
    # selection highlight walks down the list, easing between stops
    n = len(rows)
    frames = [f"{i / n * 100:.1f}%,{(i + .82) / n * 100:.1f}%{{transform:translateY({i * rh}px)}}" for i in range(n)]
    frames.append("100%{transform:translateY(0px)}")
    body += f'<rect x="{wx + 8}" y="{ry}" width="{ww - 16}" height="{rh - 4}" rx="9" fill="{t["muted"]}" class="sel"/>'
    for i, (ic, name, tech) in enumerate(rows):
        y = ry + i * rh
        body += (f'<rect x="{wx + 18}" y="{y + 7}" width="28" height="28" rx="7" fill="{t["card"]}" stroke="{t["border"]}"/>'
                 + icon(ic, wx + 24, y + 13, 16, t["fg"])
                 + f'<text x="{wx + 58}" y="{y + 26}" font-size="15" font-weight="500" fill="{t["fg"]}">{name}</text>'
                 f'<text x="{wx + ww - 22}" y="{y + 26}" text-anchor="end" font-size="13" fill="{t["muted_fg"]}">{escape(tech)}</text>')
    # cmdk-style footer with keyboard hints
    fy = ry + n * rh + 8
    body += (f'<path d="M{wx + .5} {fy}H{wx + ww - .5}V{wy + wh - 14}A13.5 13.5 0 0 1 {wx + ww - 14} {wy + wh - .5}H{wx + 14}A13.5 13.5 0 0 1 {wx + .5} {wy + wh - 14}z" fill="{t["muted"]}" fill-opacity=".45"/>'
             f'<line x1="{wx}" y1="{fy}" x2="{wx + ww}" y2="{fy}" stroke="{t["border"]}"/>'
             + icon("sparkles", wx + 20, fy + 13, 16, t["muted_fg"])
             + f'<text x="{wx + 44}" y="{fy + 26}" font-size="12" font-weight="500" fill="{t["muted_fg"]}">hitheshkaranth</text>')
    kx = wx + ww - 20
    for label, keys in (("Open", ["↵"]), ("Navigate", ["↓", "↑"])):
        kx -= tw(label, 12, 500) + 2
        body += f'<text x="{kx:.0f}" y="{fy + 26}" font-size="12" font-weight="500" fill="{t["muted_fg"]}">{label}</text>'
        for k in keys:
            kx -= 26
            body += (f'<rect x="{kx:.0f}" y="{fy + 10}" width="20" height="22" rx="5" fill="{t["card"]}" stroke="{t["border"]}"/>'
                     f'<text x="{kx + 10:.0f}" y="{fy + 25.5}" text-anchor="middle" font-size="12" font-weight="600" fill="{t["muted_fg"]}">{k}</text>')
        kx -= 18
    body += f'<rect x="{wx + .5}" y="{wy + .5}" width="{ww - 1}" height="{wh - 1}" rx="14" fill="none" stroke="{t["border"]}"/>'

    style = ("@keyframes sel{" + "".join(frames) + "}"
             f".sel{{animation:sel {n * 1.6}s cubic-bezier(.4,0,.2,1) infinite}}"
             "@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}.caret{animation:blink 1.1s steps(1) infinite}"
             "@keyframes aura{50%{opacity:.6}}.aura{animation:aura 8s ease-in-out infinite}"
             "@media (prefers-reduced-motion:reduce){*{animation:none!important}}")
    return svg(W, H, body, defs, style)


def bento(t, theme):
    W, H = 1200, 404
    tiles = [
        (8, 8, 584, 190, "plane", "Aerospace & Defence",
         ["Avionics data loading, high-reliability control and", "safety-critical firmware for aircraft systems."]),
        (600, 8, 292, 190, "cpu", "Embedded", ["STM32 · ESP32 · Embedded", "Linux HMI · telemetry"]),
        (900, 8, 292, 190, "wrench", "Developer Tools", ["AI-native IDEs, verification", "pipelines, traceability"]),
        (8, 206, 388, 190, "sparkles", "Applied AI", ["Voice assistants, research agents", "and knowledge graphs"]),
        (404, 206, 788, 190, "zap", "MLOps & Inference",
         ["Serving 35B mixture-of-experts models on a single NVIDIA DGX Spark.", "vLLM · NVFP4 / FP8 quantization · speculative decoding · observability"]),
    ]
    defs = shadow_sm(t)
    body = ""
    for x, y, w, h, ic, title, lines in tiles:
        body += (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{t["card"]}" stroke="{t["border"]}" filter="url(#sm)"/>'
                 f'<rect x="{x + 24}" y="{y + 24}" width="40" height="40" rx="10" fill="{t["muted"]}" stroke="{t["border"]}"/>'
                 + icon(ic, x + 34, y + 34, 20, t["fg"])
                 + f'<text x="{x + 24}" y="{y + 104}" font-size="18" font-weight="600" letter-spacing="-0.3" fill="{t["fg"]}">{escape(title)}</text>')
        for j, line in enumerate(lines):
            body += f'<text x="{x + 24}" y="{y + 132 + j * 22}" font-size="15" fill="{t["muted_fg"]}">{escape(line)}</text>'
    return svg(W, H, body, defs)


def heading(t, title, sub, theme):
    """shadcn page header: tight semibold title, muted description, separator."""
    W, H = 1200, 104
    body = (f'<text x="8" y="44" font-size="30" font-weight="700" letter-spacing="-0.8" fill="{t["fg"]}">{escape(title)}</text>'
            f'<text x="8" y="74" font-size="16" fill="{t["muted_fg"]}">{escape(sub)}</text>'
            f'<line x1="8" y1="95.5" x2="{W - 8}" y2="95.5" stroke="{t["border"]}"/>')
    return svg(W, H, body)


def inference(t, theme):
    """Three shadcn dashboard stat cards."""
    W, H = 1200, 196
    cols = [("Ornith-1.5", "351.7", "tok/s aggregate · 16 users", "NVFP4 + FP8 + MTP · vision", True),
            ("Qwen3.8 Distill", "373", "tok/s aggregate · 16 users", "Self-quantized, data-free", False),
            ("Qwen3.6", "219", "tok/s peak · 12 users", "Prefix cache, 5.1× faster", False)]
    cw = (W - 16 - 2 * 16) / 3
    defs = shadow_sm(t)
    body = ""
    for i, (name, num, unit, note, live) in enumerate(cols):
        x = 8 + i * (cw + 16)
        body += (f'<rect x="{x:.0f}" y="8" width="{cw:.0f}" height="{H - 16}" rx="14" fill="{t["card"]}" stroke="{t["border"]}" filter="url(#sm)"/>'
                 f'<text x="{x + 24:.0f}" y="44" font-size="14" font-weight="500" fill="{t["fg"]}">{name}</text>'
                 + icon("zap", x + cw - 40, 30, 16, t["muted_fg"])
                 + f'<text x="{x + 24:.0f}" y="100" font-size="40" font-weight="700" letter-spacing="-1.2" fill="{t["fg"]}">{num}</text>'
                 f'<text x="{x + 24:.0f}" y="128" font-size="13" fill="{t["muted_fg"]}">{unit}</text>'
                 f'<text x="{x + 24:.0f}" y="160" font-size="13" fill="{t["muted_fg"]}">{note}</text>')
        if live:
            nw = tw(num, 40, 700) - 8
            body += (f'<rect x="{x + 24 + nw + 14:.0f}" y="76" width="56" height="22" rx="11" fill="{t["live_bg"]}"/>'
                     f'<circle cx="{x + 24 + nw + 26:.0f}" cy="87" r="3.5" fill="#22c55e" class="pulse"/>'
                     f'<text x="{x + 24 + nw + 34:.0f}" y="91.5" font-size="12" font-weight="600" fill="{t["live_fg"]}">Live</text>')
    style = "@keyframes pulse{50%{opacity:.3}}.pulse{animation:pulse 1.8s ease-in-out infinite}"
    return svg(W, H, body, defs, style)


def stack(t, theme):
    """shadcn <Table> inside a card: layer → technologies."""
    layers = [("sparkles", "Intelligence", ["vLLM", "NVFP4 / FP8", "Speculative decoding", "Voice AI", "Agents", "Claude · Gemini · Codex"]),
              ("wrench", "Tools", ["TypeScript", "React", "Tauri", "Code-OSS", "FastAPI", "PySide6"]),
              ("shield", "Assurance", ["DO-178C", "MISRA", "CBMC", "CodeQL", "MC/DC", "Traceability"]),
              ("plane", "Systems", ["C++23", "Rust", "Qt 6", "Embedded Linux", "VxWorks", "ARINC 615A / 665"]),
              ("cpu", "Silicon", ["C", "STM32", "ESP32", "LVGL", "CAN · UART · USB", "Sensor telemetry"])]
    W, hh, rh = 1200, 44, 58
    H = 16 + hh + len(layers) * rh
    defs = shadow_sm(t) + f'<clipPath id="tbl"><rect x="8" y="8" width="{W - 16}" height="{H - 16}" rx="14"/></clipPath>'
    body = (f'<rect x="8" y="8" width="{W - 16}" height="{H - 16}" rx="14" fill="{t["card"]}" filter="url(#sm)"/>'
            f'<g clip-path="url(#tbl)"><rect x="8" y="8" width="{W - 16}" height="{hh}" fill="{t["muted"]}" fill-opacity=".5"/></g>'
            f'<text x="32" y="{8 + hh / 2 + 5}" font-size="13" font-weight="500" fill="{t["muted_fg"]}">Layer</text>'
            f'<text x="240" y="{8 + hh / 2 + 5}" font-size="13" font-weight="500" fill="{t["muted_fg"]}">Technologies</text>')
    for i, (ic, name, items) in enumerate(layers):
        y = 8 + hh + i * rh
        body += f'<line x1="8" y1="{y}" x2="{W - 8}" y2="{y}" stroke="{t["border"]}"/>'
        body += (icon(ic, 32, y + rh / 2 - 9, 18, t["fg"])
                 + f'<text x="60" y="{y + rh / 2 + 5}" font-size="15" font-weight="500" fill="{t["fg"]}">{name}</text>')
        x = 240
        for it in items:
            w, b = badge(t, x, y + rh / 2 - 11, it, "secondary")
            body += b
            x += w + 6
    body += f'<rect x="8.5" y="8.5" width="{W - 17}" height="{H - 17}" rx="14" fill="none" stroke="{t["border"]}"/>'
    return svg(W, H, body, defs)


def link_button(t, kind):
    label, ic, variant = {"x": ("@HitheshKaranth", "x", "outline"),
                          "web": ("FlyVI Technologies", "globe", "outline"),
                          "repos": ("Repositories", "folder", "outline"),
                          "github": ("Follow on GitHub", "github", "default")}[kind]
    w, b = button(t, 4, 4, label, variant, lead=ic, h=40)
    W = int(w) + 8
    return svg(W, 48, f'<g filter="url(#sm)">{b}</g>', shadow_sm(t))


def footer(t, theme):
    W, H = 1200, 64
    body = (f'<line x1="8" y1="8.5" x2="{W - 8}" y2="8.5" stroke="{t["border"]}"/>'
            f'<text x="8" y="44" font-size="14" fill="{t["muted_fg"]}">Hithesh Karanth</text>'
            f'<text x="{W - 8}" y="44" text-anchor="end" font-size="14" fill="{t["muted_fg"]}">Thanks for stopping by.</text>')
    return svg(W, H, body)

# ── main ─────────────────────────────────────────────────────────────────────

WIDE = {"noyce", "wirevoice", "openterminalui", "arinc", "ornith"}
HEADINGS = {
    "about": ("About", "Aerospace, embedded systems, developer tools and applied AI."),
    "now": ("Building now", "What I'm shipping at the moment."),
    "award": ("Recognition", "Hackathons and awards."),
    "oss": ("Open source", "Projects anyone can run, fork and extend."),
    "systems": ("Systems work", "Avionics, firmware and hardware tooling."),
    "mlops": ("Inference", "Self-hosted LLM serving on NVIDIA DGX Spark. Every number measured on the live deployment."),
    "stack": ("Stack", "From silicon to intelligence, layer by layer."),
    "stars": ("Star history", "How the open-source projects have grown."),
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.svg"):
        old.unlink()
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
            files[f"btn-{k}-{theme}.svg"] = link_button(t, k)
        for name, content in files.items():
            (OUT / name).write_text(content)
    # Stamp README image links with a content hash so browsers and GitHub's
    # image cache fetch the new artwork as soon as it changes.
    digest = hashlib.sha1(b"".join(f.read_bytes() for f in sorted(OUT.glob("*.svg")))).hexdigest()[:8]
    readme = ROOT / "README.md"
    text = re.sub(r'(\./assets/gen/[\w.-]+\.svg)(\?v=\w+)?', rf"\1?v={digest}", readme.read_text())
    # GitHub's image proxy caches the star-history chart too; bust it once a day.
    day = __import__("datetime").date.today().strftime("%Y%m%d")
    text = re.sub(r'(api\.star-history\.com/svg\?[^"]*?)(&v=\d+)?"', rf'\1&v={day}"', text)
    readme.write_text(text)
    print(f"wrote {len(list(OUT.glob('*.svg')))} files to {OUT.relative_to(ROOT)}, version {digest}")


if __name__ == "__main__":
    main()
