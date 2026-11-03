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
    "skanda": dict(repo=None, logo="skanda.png", accent="#0ea5e9", private=True,
        eyebrow="Custom model", title="Skanda Grounding",
        tagline="Reads X-ray, CT and MRI. Outlines every finding. Explains each outline.",
        desc="A 31B vision-language model I fine-tuned end to end on one DGX Spark: Qwen3-VL-30B-A3B writes the "
             "report, a [SEG] token per finding drives SAM 2.1 to draw the outline, and every number in the evidence "
             "is measured from radiologist masks. Trained only on commercially licensed data.",
        meta="Qwen3-VL · SAM 2.1 · LoRA · DGX Spark", stars=False),
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
        meta="TypeScript · React · Python · FastAPI", badge="MIT", award="Stanford × DeepMind Hackathon"),
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


MONO = "ui-monospace, 'SF Mono', SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"
RM = "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"


def svg(w, h, body, defs="", style=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{w}" height="{h}" viewBox="0 0 {w} {h}" font-family="{FONT}">'
            f'<style>{style}{RM}</style><defs>{defs}</defs>{body}</svg>\n')


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
    "scan": '<path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2"/><circle cx="12" cy="12" r="1"/><path d="M18.944 12.33a1 1 0 0 0 0-.66 7.5 7.5 0 0 0-13.888 0 1 1 0 0 0 0 .66 7.5 7.5 0 0 0 13.888 0"/>',
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
    W, H = (1200, 410) if wide else (600, 470)
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
    for line in wrap(p["desc"], 70 if wide else 72):
        body += f'<text x="{32 if not wide else tx}" y="{y}" font-size="15" fill="{t["muted_fg"]}">{escape(line)}</text>'
        y += 24

    # the project's ASCII scene
    sy = H - 76
    if wide:
        body += ascii_panel(t, key, p, W - 32 - 500, 92, 500, sy - 18 - 92, 11)
    else:
        body += ascii_panel(t, key, p, 32, y - 6, W - 64, sy - 18 - (y - 6), 10.5)

    # footer: separator, tech badges, action
    body += f'<line x1="9" y1="{sy}" x2="{W - 9}" y2="{sy}" stroke="{t["border"]}"/>'
    bx = 32
    for tech in [s.strip() for s in p["meta"].split("·")]:
        w, b = badge(t, bx, sy + 23, tech, "outline")
        body += b
        bx += w + 6
    if p.get("private"):  # private repo: say so instead of offering a link that 404s
        w, _ = badge(t, 0, 0, "Private research · weights on request", "outline", lead="shield")
        body += badge(t, W - 32 - w, sy + 23, "Private research · weights on request", "outline", lead="shield")[1]
    else:
        label = "View repository" if p.get("repo") else "Read announcement"
        w, _ = button(t, 0, 0, label, "outline", trail="arrow")
        body += button(t, W - 32 - w, sy + 16, label, "outline", trail="arrow")[1]
    return svg(W, H, body, defs)


# ── Skanda: custom model training ────────────────────────────────────────────

SKANDA = {"light": "#0284c7", "dark": "#38bdf8"}   # sky, ≥4.5:1 on the card in both themes
BASE = {"light": "#a1a1aa", "dark": "#52525b"}     # MedGemma baseline bars
SEG_GOLD = "#eab308"                                # radiologist outline colour used in the reads

# Held-out benchmark, % (higher is better). Skanda run 3 = the published checkpoint.
# Source: skanda-grounding README, "Results" (same runner and scorer for every model).
BENCH = [("Chest X-ray", "111 films", [("Normals called normal", 72, 69), ("Right finding type", 41, 40.5), ("Box precision", 6, 25.5)]),
         ("CT", "340 cases", [("Normals called normal", 6, 91), ("Right finding type", 49, 72), ("Box precision", 1, 22)]),
         ("MRI", "240 cases", [("Normals called normal", 2, 94), ("Right finding type", 42, 89), ("Box precision", 6, 70)])]


def fmt(v):
    return f"{v:g}"


def skanda_bench(t, theme):
    """Grouped horizontal bars with direct value labels: colour is never the only cue."""
    W, H = 1200, 432
    acc, base = SKANDA[theme], BASE[theme]
    defs = shadow_sm(t)
    body = frame(t, W, H)
    body += (f'<text x="32" y="56" font-size="20" font-weight="600" letter-spacing="-0.4" fill="{t["fg"]}">Held-out benchmark</text>'
             f'<text x="32" y="80" font-size="14" fill="{t["muted_fg"]}">Skanda run 3 vs MedGemma 27B · same runner and scorer for every model · % (higher is better)</text>')
    # legend, top right
    lx = W - 32 - 300
    body += (f'<rect x="{lx}" y="44" width="14" height="10" rx="3" fill="{base}"/>'
             f'<text x="{lx + 20}" y="54" font-size="13" fill="{t["muted_fg"]}">MedGemma 27B</text>'
             f'<rect x="{lx + 140}" y="44" width="14" height="10" rx="3" fill="{acc}"/>'
             f'<text x="{lx + 160}" y="54" font-size="13" font-weight="600" fill="{t["fg"]}">Skanda run 3</text>')
    body += f'<line x1="9" y1="104" x2="{W - 9}" y2="104" stroke="{t["border"]}"/>'
    pw, gap = (W - 64 - 2 * 32) / 3, 32
    for i, (name, n, rows) in enumerate(BENCH):
        x = 32 + i * (pw + gap)
        if i:
            body += f'<line x1="{x - gap / 2:.0f}" y1="124" x2="{x - gap / 2:.0f}" y2="{H - 74}" stroke="{t["border"]}"/>'
        body += (f'<text x="{x:.0f}" y="138" font-size="16" font-weight="600" fill="{t["fg"]}">{name}</text>'
                 f'<text x="{x + tw(name, 16, 600) + 10:.0f}" y="138" font-size="13" fill="{t["muted_fg"]}">{n}</text>')
        bw = pw - 54  # room for the value label
        y = 168
        for label, mg, sk in rows:
            body += f'<text x="{x:.0f}" y="{y}" font-size="13" fill="{t["muted_fg"]}">{label}</text>'
            for j, (v, c, strong) in enumerate(((mg, base, False), (sk, acc, True))):
                by = y + 10 + j * 18
                body += (f'<rect x="{x:.0f}" y="{by}" width="{bw:.0f}" height="12" rx="3" fill="{t["muted"]}" fill-opacity=".6"/>'
                         f'<rect x="{x:.0f}" y="{by}" width="{max(bw * v / 100, 3):.1f}" height="12" rx="3" fill="{c}"/>'
                         f'<text x="{x + bw + 10:.0f}" y="{by + 11}" font-size="13" font-weight="{600 if strong else 400}" '
                         f'fill="{t["fg"] if strong else t["muted_fg"]}">{fmt(v)}</text>')
            y += 76
    body += (f'<line x1="9" y1="{H - 62}" x2="{W - 9}" y2="{H - 62}" stroke="{t["border"]}"/>'
             f'<text x="32" y="{H - 34}" font-size="13" fill="{t["muted_fg"]}">CT and MRI: Skanda names the right finding 72% / 89% of the time and clears 91% / 94% of lesion-free scans. '
             f'Chest X-ray is a trade: small test set (±10 pts).</text>')
    return svg(W, H, body, defs)


def jpeg_uri(name):
    return "data:image/jpeg;base64," + base64.b64encode((ASSETS / name).read_bytes()).decode()


def skanda_reads(t, theme):
    """Real held-out reads: MedGemma beside Skanda, per modality."""
    W, H = 1200, 404
    acc = SKANDA[theme]
    cases = [("xray", "Chest X-ray", "effusion + consolidation", "0.50", "0.89"),
             ("ct", "CT", "right lung tumour", "0.01", "0.91"),
             ("mri", "MRI", "brain tumour with oedema", "0.24", "0.97")]
    defs = shadow_sm(t)
    body = frame(t, W, H)
    body += (f'<text x="32" y="56" font-size="20" font-weight="600" letter-spacing="-0.4" fill="{t["fg"]}">Same scan, two readers</text>'
             f'<text x="32" y="80" font-size="14" fill="{t["muted_fg"]}">Saved benchmark reads on held-out cases. IoU = box overlap with the radiologist&apos;s outline.</text>')
    cw, gap, im, ig = 360, 28, 172, 16
    for i, (key, name, what, mg, sk) in enumerate(cases):
        x = 32 + i * (cw + gap)
        if i:
            body += f'<line x1="{x - gap / 2}" y1="112" x2="{x - gap / 2}" y2="{H - 74}" stroke="{t["border"]}"/>'
        body += (f'<text x="{x}" y="124" font-size="16" font-weight="600" fill="{t["fg"]}">{name}</text>'
                 f'<text x="{x + tw(name, 16, 600) + 10:.0f}" y="124" font-size="13" fill="{t["muted_fg"]}">{what}</text>')
        for j, (who, iou, strong) in enumerate((("MedGemma 27B", mg, False), ("Skanda", sk, True))):
            ix, iy = x + j * (im + ig), 140
            cid = f"r{i}{j}"
            defs += f'<clipPath id="{cid}"><rect x="{ix}" y="{iy}" width="{im}" height="{im}" rx="10"/></clipPath>'
            body += (f'<image x="{ix}" y="{iy}" width="{im}" height="{im}" href="{jpeg_uri(f"skanda-read-{key}-{"medgemma" if j == 0 else "skanda"}.jpg")}" clip-path="url(#{cid})" preserveAspectRatio="xMidYMid slice"/>'
                     f'<rect x="{ix + .5}" y="{iy + .5}" width="{im - 1}" height="{im - 1}" rx="10" fill="none" stroke="{acc if strong else t["border"]}" stroke-width="{1.5 if strong else 1}"/>'
                     f'<text x="{ix}" y="{iy + im + 22}" font-size="13" fill="{t["muted_fg"]}">{who}</text>'
                     f'<text x="{ix + im}" y="{iy + im + 22}" text-anchor="end" font-size="13" font-weight="{600 if strong else 400}" fill="{t["fg"] if strong else t["muted_fg"]}">IoU {iou}</text>')
    # legend: line style + colour + words
    ly = H - 34
    body += f'<line x1="9" y1="{H - 62}" x2="{W - 9}" y2="{H - 62}" stroke="{t["border"]}"/>'
    body += (f'<line x1="32" y1="{ly - 4}" x2="56" y2="{ly - 4}" stroke="{SEG_GOLD}" stroke-width="2" stroke-dasharray="5 3"/>'
             f'<text x="64" y="{ly}" font-size="13" fill="{t["muted_fg"]}">Radiologist</text>'
             f'<line x1="170" y1="{ly - 4}" x2="194" y2="{ly - 4}" stroke="#94a3b8" stroke-width="2"/>'
             f'<text x="202" y="{ly}" font-size="13" fill="{t["muted_fg"]}">MedGemma box</text>'
             f'<line x1="330" y1="{ly - 4}" x2="354" y2="{ly - 4}" stroke="#38bdf8" stroke-width="3"/>'
             f'<text x="362" y="{ly}" font-size="13" fill="{t["muted_fg"]}">Skanda outline + box</text>'
             f'<text x="{W - 32}" y="{ly}" text-anchor="end" font-size="13" fill="{t["muted_fg"]}">Cases chosen by a fixed rule; the benchmark shows how often.</text>')
    return svg(W, H, body, defs)


def hero(t, theme):
    W, H = 1200, 816
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
            ("scan", "Training", "Qwen3-VL · SAM 2 · LoRA · GRPO"),
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
             )
    return svg(W, H, body, defs, style)


def bento(t, theme):
    W, H = 1200, 404
    tiles = [
        (8, 8, 584, 190, "plane", "Aerospace & Defence",
         ["Avionics data loading, high-reliability control and", "safety-critical firmware for aircraft systems."]),
        (600, 8, 292, 190, "cpu", "Embedded", ["STM32 · ESP32 · Embedded", "Linux HMI · telemetry"]),
        (900, 8, 292, 190, "wrench", "Developer Tools", ["AI-native IDEs, verification", "pipelines, traceability"]),
        (8, 206, 388, 190, "scan", "Model Training", ["Grounded radiology VLMs, voice", "assistants and research agents"]),
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


def heading(t, title, sub, theme, slug=""):
    """Shell prompt, then a tight semibold title, muted description, separator."""
    W, H = 1200, 126
    body = (f'<text x="8" y="22" font-family="{MONO}" font-size="13" xml:space="preserve">'
            f'<tspan fill="{"#4ade80" if theme == "dark" else "#15803d"}">❯</tspan><tspan fill="{t["muted_fg"]}"> cd ~/{slug}</tspan></text>'
            f'<text x="8" y="64" font-size="30" font-weight="700" letter-spacing="-0.8" fill="{t["fg"]}">{escape(title)}</text>'
            f'<text x="8" y="94" font-size="16" fill="{t["muted_fg"]}">{escape(sub)}</text>'
            f'<line x1="8" y1="117.5" x2="{W - 8}" y2="117.5" stroke="{t["border"]}"/>')
    return svg(W, H, body)


def inference(t, theme):
    """Three shadcn dashboard stat cards."""
    W, H = 1200, 216
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
        cells = 30
        full = round(cells * float(num) / 400)  # scale: 400 tok/s
        body += (f'<text x="{x + 24:.0f}" y="184" font-family="{MONO}" font-size="12" xml:space="preserve">'
                 f'<tspan fill="{t["muted_fg"]}">[</tspan><tspan fill="#76b900">{"#" * full}</tspan>'
                 f'<tspan fill="{t["border"]}">{"." * (cells - full)}</tspan><tspan fill="{t["muted_fg"]}">] {num}/400</tspan></text>')
        if live:
            nw = tw(num, 40, 700) - 8
            body += (f'<rect x="{x + 24 + nw + 14:.0f}" y="76" width="64" height="22" rx="11" fill="{t["live_bg"]}"/>'
                     + flipbook(SPIN, x + 24 + nw + 22, 92, 13, t["live_fg"], 1.0, MONO)
                     + f'<text x="{x + 24 + nw + 38:.0f}" y="91.5" font-size="12" font-weight="600" fill="{t["live_fg"]}">Live</text>')
    return svg(W, H, body, defs, FLIP)


def stack(t, theme):
    """shadcn <Table> inside a card: layer → technologies."""
    layers = [("sparkles", "Intelligence", ["vLLM", "NVFP4 / FP8", "Speculative decoding", "Voice AI", "Agents", "Claude · Gemini · Codex"]),
              ("scan", "Training", ["Qwen3-VL", "SAM 2.1", "PEFT / LoRA", "GRPO", "MONAI", "Grafana"]),
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
    label, ic, variant = {"site": ("hitheshkaranth.dev", "globe", "outline"),
                          "x": ("@HitheshKaranth", "x", "outline"),
                          "web": ("FlyVI Technologies", "plane", "outline"),
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

# ── ASCII / terminal ─────────────────────────────────────────────────────────
# Rule: the first frame of every animation is a complete picture, because some
# viewers (previews, paused or headless renderers) only ever show frame 0.

TERM = dict(bg="#0a0a0c", bar="#141417", fg="#e4e4e7", muted="#71717a", dim="#3f3f46",
            green="#4ade80", sky="#38bdf8", amber="#fbbf24", pink="#f472b6")
SPIN = list("⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏")
FLIP = ""
NAME_ART = ['    __  ___ __  __              __       __ __                       __  __',
            '   / / / (_) /_/ /_  ___  _____/ /_     / //_/___ __________ _____  / /_/ /_',
            '  / /_/ / / __/ __ \\/ _ \\/ ___/ __ \\   / ,< / __ `/ ___/ __ `/ __ \\/ __/ __ \\',
            ' / __  / / /_/ / / /  __(__  ) / / /  / /| / /_/ / /  / /_/ / / / / /_/ / / /',
            '/_/ /_/_/\\__/_/ /_/\\___/____/_/ /_/  /_/ |_\\__,_/_/   \\__,_/_/ /_/\\__/_/ /_/']  # pyfiglet "slant"


def lines_text(lines, x, y, size, lh, fill, extra=""):
    """A block of monospace lines; spaces preserved so columns line up."""
    out = f'<text x="{x}" y="{y}" font-family="{MONO}" font-size="{size}" fill="{fill}" xml:space="preserve"{extra}>'
    for j, ln in enumerate(lines):
        if ln.strip():
            out += (f'<tspan x="{x}" y="{y + j * lh:.1f}" textLength="{len(ln) * size * .6:.0f}" '
                    f'lengthAdjust="spacingAndGlyphs">{escape(ln)}</tspan>')
    return out + '</text>'


def flipbook(frames, x, y, size, fill, period, family=None, lh=None):
    """Frame-by-frame animation: one frame visible at a time, frame 0 when still.
    Each frame is a string (one line) or a list of (lines, fill) layers."""
    n = len(frames)
    name = f"fb{n}x{int(period * 100)}"  # unique per frame count and speed
    out = (f'<style>@keyframes {name}{{0%{{opacity:1}}{100 / n - .005:.3f}%,100%{{opacity:0}}}}'
           f'.{name}{{animation:{name} {period}s steps(1,end) infinite}}</style>')
    for k, fr in enumerate(frames):
        attrs = f' class="{name}" style="animation-delay:{-k * period / n:.3f}s"' + ('' if k == 0 else ' opacity="0"')
        if isinstance(fr, str):
            out += (f'<text x="{x}" y="{y}" font-family="{family or MONO}" font-size="{size}" fill="{fill}"{attrs}>'
                    f'{escape(fr)}</text>')
        else:
            out += f'<g{attrs}>' + "".join(lines_text(ls, x, y, size, lh, f) for ls, f in fr) + '</g>'
    return out


def torus_frames(cols=64, rows=30, n=36):
    """The classic spinning ASCII torus (after Andy Sloane's donut.c), split into
    a dim and a bright layer per frame so the lighting reads in two colours."""
    import math
    ramp = ".,-~:;=!*#$@"
    frames = []
    for k in range(n):
        A, B = 1.0 + 2 * math.pi * k / n, 0.6 + 2 * math.pi * k / n
        z = [[0.0] * cols for _ in range(rows)]
        out = [[" "] * cols for _ in range(rows)]
        cA, sA, cB, sB = math.cos(A), math.sin(A), math.cos(B), math.sin(B)
        th = 0.0
        while th < 2 * math.pi:
            ct, st = math.cos(th), math.sin(th)
            ph = 0.0
            while ph < 2 * math.pi:
                cp, sp = math.cos(ph), math.sin(ph)
                cx, cy = 2 + ct, st                      # R2 + R1·cosθ, R1·sinθ
                x = cx * (cB * cp + sA * sB * sp) - cy * cA * sB
                y = cx * (sB * cp - sA * cB * sp) + cy * cA * cB
                ooz = 1 / (5 + cA * cx * sp + cy * sA)
                xp = int(cols / 2 + 38 * ooz * x)
                yp = int(rows / 2 - 19 * ooz * y)
                L = cp * ct * sB - cA * ct * sp - sA * st + cB * (cA * st - ct * sA * sp)
                if 0 <= xp < cols and 0 <= yp < rows and ooz > z[yp][xp]:
                    z[yp][xp] = ooz
                    out[yp][xp] = ramp[max(0, int(L * 8))] if L > 0 else "."
                ph += 0.025
            th += 0.06
        rowsS = ["".join(r).rstrip() for r in out]
        tone = lambda keep: ["".join(c if c in keep else " " for c in r) for r in rowsS]
        frames.append([(tone(".,-~"), TERM["dim"]), (tone(":;=!"), TERM["muted"]), (tone("*#"), TERM["fg"]), (tone("$@"), TERM["sky"])])
    return frames


def term_window(t, W, H, title):
    """macOS-style terminal window: always dark, in both themes."""
    return (f'<rect x="8" y="8" width="{W - 16}" height="{H - 16}" rx="14" fill="{TERM["bg"]}" stroke="{t["border"]}" filter="url(#sm)"/>'
            f'<path d="M22 8.5H{W - 22}A13.5 13.5 0 0 1 {W - 8.5} 22V44H8.5V22A13.5 13.5 0 0 1 22 8.5z" fill="{TERM["bar"]}"/>'
            f'<line x1="8.5" y1="44" x2="{W - 8.5}" y2="44" stroke="#27272a"/>'
            f'<circle cx="30" cy="26" r="6" fill="#ff5f57"/><circle cx="50" cy="26" r="6" fill="#febc2e"/><circle cx="70" cy="26" r="6" fill="#28c840"/>'
            f'<text x="{W / 2}" y="31" text-anchor="middle" font-family="{MONO}" font-size="12" fill="{TERM["muted"]}">{escape(title)}</text>')


def prompt(x, y, cmd, size=14):
    return (f'<text x="{x}" y="{y}" font-family="{MONO}" font-size="{size}" xml:space="preserve">'
            f'<tspan fill="{TERM["green"]}">❯</tspan><tspan fill="{TERM["fg"]}"> {escape(cmd)}</tspan></text>')


def cursor(x, y, size=14):
    return (f'<rect x="{x}" y="{y - size + 2}" width="{size * .6:.1f}" height="{size + 2}" fill="{TERM["fg"]}" class="cur"/>'
            '<style>@keyframes cur{0%,49%{opacity:1}50%,100%{opacity:0}}.cur{animation:cur 1.1s steps(1) infinite}</style>')


def ascii_hero(t, theme):
    W, H = 1200, 452
    cw = 14 * .6  # monospace advance at 14px
    defs = shadow_sm(t) + (f'<linearGradient id="nameInk" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fafafa"/>'
                           f'<stop offset="1" stop-color="{TERM["sky"]}"/></linearGradient>')
    body = term_window(t, W, H, "hithesh@karanth: ~ — zsh")
    body += lines_text(NAME_ART, 40, 88, 14, 17, "url(#nameInk)", ' font-weight="700"')
    y = 214
    rows = [("whoami", [[("Hithesh Karanth · CTO, FlyVI Technologies", TERM["fg"])]]),
            ("cat focus.txt", [[("From silicon to intelligence, built to be verified.", TERM["muted"])]]),
            ("ls ~/building", [[("noyce-ide/  ", TERM["sky"]), ("skanda-grounding/  ", TERM["sky"]),
                                ("openterminalui/  ", TERM["sky"]), ("embedded-display-studio/", TERM["sky"])]])]
    for cmd, outs in rows:
        body += prompt(40, y, cmd)
        y += 24
        for segs in outs:
            body += f'<text x="40" y="{y}" font-family="{MONO}" font-size="14" xml:space="preserve">'
            body += "".join(f'<tspan fill="{c}">{escape(txt)}</tspan>' for txt, c in segs) + '</text>'
            y += 30
    body += f'<text x="40" y="{y}" font-family="{MONO}" font-size="14" fill="{TERM["green"]}">❯</text>' + cursor(40 + 2 * cw, y)
    # spinning torus on the right
    body += flipbook(torus_frames(), 790, 66, 9.5, TERM["fg"], 4.8, lh=12.2)
    return svg(W, H, body, defs)


def mri_ascii(cols=60, rows=30, fine=False):
    """The held-out MRI read as ASCII: grey tissue, and the cells Skanda outlined.
    Contrast is stretched over the brain so ventricles and tumour stand out."""
    ramp = (" .'`^\",:;Il!i><~+_-?][}{1)(|/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$" if fine else " .:-=+*#%@")
    im = Image.open(ASSETS / "skanda-read-mri-skanda.jpg").convert("RGB")
    W, H = im.size
    cw, ch = W / cols, H / rows
    px = im.load()
    cells = []
    for r in range(rows):
        row = []
        for c in range(cols):
            tot = blue = 0
            lum = 0.0
            for yy in range(int(r * ch), max(int(r * ch) + 1, int((r + 1) * ch))):
                for xx in range(int(c * cw), max(int(c * cw) + 1, int((c + 1) * cw))):
                    R, G, Bc = px[xx, yy]
                    tot += 1
                    if Bc > 150 and Bc - R > 70:   # Skanda's sky-blue outline
                        blue += 1
                    lum += (0.299 * R + 0.587 * G + 0.114 * Bc) / 255
            row.append((lum / max(tot, 1), blue / max(tot, 1)))
        cells.append(row)
    tissue = sorted(l for row in cells for l, b in row if l > .08 and b < .32)
    lo, hi = (tissue[int(len(tissue) * .04)], tissue[int(len(tissue) * .985)]) if tissue else (0, 1)
    base, mask = [], []
    for row in cells:
        b_row, m_row = "", ""
        for lum, blue in row:
            if lum <= .06:
                v = 0
            else:
                v = .08 + .92 * max(0, min(1, (lum - lo) / (hi - lo + 1e-9)))
            chx = ramp[min(len(ramp) - 1, int(v ** 1.15 * (len(ramp) - 1) + .5))]
            if blue > 0.32:
                m_row += chx if chx.strip() else "+"
                b_row += " "
            else:
                b_row += chx
                m_row += " "
        base.append(b_row.rstrip())
        mask.append(m_row.rstrip())
    return base, mask


def skanda_terminal(t, theme):
    W, H = 1200, 470
    defs = shadow_sm(t)
    body = term_window(t, W, H, "skanda — reading a held-out MRI")
    base, mask = mri_ascii(cols=84, rows=40)
    sx, sy, size, lh = 36, 70, 8, 9.2
    body += lines_text(base, sx, sy, size, lh, "#8b8b94")
    # Skanda's outline, row by row: still = fully drawn; in motion = erased, then
    # re-drawn as the scan line passes (same 7 s clock for rows and line).
    period, sweep = 7.0, 2.1
    for r, row in enumerate(mask):
        if row.strip():
            body += (f'<text x="{sx}" y="{sy + r * lh:.1f}" font-family="{MONO}" font-size="{size}" font-weight="700" fill="{TERM["sky"]}" '
                     f'xml:space="preserve" textLength="{len(row) * size * .6:.1f}" lengthAdjust="spacingAndGlyphs" '
                     f'class="mrow" style="animation-delay:{r / len(mask) * sweep:.2f}s">{escape(row)}</text>')
    span = len(mask) * lh
    body += (f'<g class="scan"><rect x="{sx - 6}" y="{sy - 22}" width="{84 * size * .6 + 12}" height="20" fill="{TERM["sky"]}" fill-opacity=".10"/>'
             f'<rect x="{sx - 6}" y="{sy - 3}" width="{84 * size * .6 + 12}" height="1.5" fill="{TERM["sky"]}"/></g>')
    body += (f'<style>@keyframes mrow{{0%,36%{{opacity:1}}39%,44%{{opacity:0}}46%,100%{{opacity:1}}}}'
             f'.mrow{{animation:mrow {period}s linear infinite}}'
             f'@keyframes scan{{0%,44%{{transform:translateY(0);opacity:0}}45%{{opacity:1}}74%{{transform:translateY({span:.0f}px);opacity:1}}'
             f'75%,100%{{transform:translateY({span:.0f}px);opacity:0}}}}.scan{{animation:scan {period}s linear infinite}}</style>')
    body += (f'<text x="{sx}" y="{sy + span + 18:.0f}" font-family="{MONO}" font-size="11" fill="{TERM["muted"]}">'
             f'BRATS_234_z78 · held out · </text>'
             f'<text x="{sx + 27 * 6.6:.0f}" y="{sy + span + 18:.0f}" font-family="{MONO}" font-size="11" fill="{TERM["sky"]}">█ Skanda outline</text>')
    # the reply, syntax-highlighted
    K, S, P, M = TERM["sky"], TERM["green"], TERM["muted"], TERM["fg"]
    x, y, lh2 = 484, 84, 22
    body += prompt(x, y, "curl -s spark:1234/v1/chat/completions -d @BRATS_234.json | jq", 12.5)
    reply = [[("{", P)],
             [('  "normal"', K), (": ", P), ("false", TERM["amber"]), (",", P)],
             [('  "findings"', K), (": [", P)]]
    for title in ("Oedema", "Non-enhancing tumour", "Enhancing tumour"):
        reply.append([("    { ", P), ('"title"', K), (": ", P), (f'"{title}"', S), (", ", P), ('"side"', K), (": ", P),
                      ('"right"', S), (", ", P), ('"mask"', K), (": ", P), ('"[SEG]"', TERM["pink"]), (" }", P)])
    reply += [[("  ]", P)], [("}", P)]]
    y += lh2 + 6
    for segs in reply:
        body += f'<text x="{x}" y="{y}" font-family="{MONO}" font-size="13" xml:space="preserve">'
        body += "".join(f'<tspan fill="{c}">{escape(txt)}</tspan>' for txt, c in segs) + '</text>'
        y += lh2
    y += 8
    body += (f'<text x="{x}" y="{y}" font-family="{MONO}" font-size="13" xml:space="preserve"><tspan fill="{P}"># each </tspan>'
             f'<tspan fill="{TERM["pink"]}">[SEG]</tspan><tspan fill="{P}"> becomes one outline · IoU </tspan>'
             f'<tspan fill="{M}" font-weight="700">0.97</tspan><tspan fill="{P}"> vs radiologist (MedGemma 27B: 0.24)</tspan></text>')
    y += lh2 + 10
    body += f'<text x="{x}" y="{y}" font-family="{MONO}" font-size="13" fill="{TERM["green"]}">❯</text>' + cursor(x + 2 * 13 * .6, y, 13)
    return svg(W, H, body, defs)



# ── per-project ASCII scenes ─────────────────────────────────────────────────
# Each scene draws on a Grid (characters + colours, with braille sub-pixels for
# curves) and returns frames. Frame 0 is always the finished picture.

import math
import random as _random

_BR = {(0, 0): 0x01, (0, 1): 0x02, (0, 2): 0x04, (1, 0): 0x08, (1, 1): 0x10, (1, 2): 0x20, (0, 3): 0x40, (1, 3): 0x80}
RED = "#f87171"


class Grid:
    def __init__(self, cols, rows):
        self.c, self.r = cols, rows
        self.cell = [[(" ", None)] * cols for _ in range(rows)]

    def put(self, r, c, text, color):
        for i, ch in enumerate(text):
            if 0 <= r < self.r and 0 <= c + i < self.c:
                self.cell[r][c + i] = (ch, color)
        return c + len(text)

    def puts(self, r, c, *segs):
        for text, color in segs:
            c = self.put(r, c, text, color)
        return c

    def dots(self, pts, color, r0=0, c0=0):
        """Plot sub-pixel points (2 wide × 4 tall per cell) as braille."""
        acc = {}
        for x, y in pts:
            x, y = int(round(x)), int(round(y))
            if x < 0 or y < 0:
                continue
            cc, rr = c0 + x // 2, r0 + y // 4
            if 0 <= rr < self.r and 0 <= cc < self.c:
                acc[(rr, cc)] = acc.get((rr, cc), 0) | _BR[(x % 2, y % 4)]
        for (rr, cc), bits in acc.items():
            ch, _ = self.cell[rr][cc]
            if 0x2800 <= ord(ch) <= 0x28FF:
                bits |= ord(ch) - 0x2800
            elif ch != " ":
                continue  # never draw over text
            self.cell[rr][cc] = (chr(0x2800 + bits), color)

    def box(self, r, c, h, w, color, title="", tcolor=None):
        self.put(r, c, "┌" + "─" * (w - 2) + "┐", color)
        for i in range(1, h - 1):
            self.put(r + i, c, "│", color)
            self.put(r + i, c + w - 1, "│", color)
        self.put(r + h - 1, c, "└" + "─" * (w - 2) + "┘", color)
        if title:
            self.put(r, c + 2, f" {title} ", tcolor or color)

    def hline(self, r, c0, c1, color, ch="─"):
        for c in range(min(c0, c1), max(c0, c1) + 1):
            self.put(r, c, ch, color)

    def vline(self, c, r0, r1, color, ch="│"):
        for r in range(min(r0, r1), max(r0, r1) + 1):
            self.put(r, c, ch, color)

    def rows(self):
        out = []
        for row in self.cell:
            segs = []
            for ch, colr in row:
                colr = colr or TERM["fg"]
                if segs and segs[-1][1] == colr:
                    segs[-1] = (segs[-1][0] + ch, colr)
                else:
                    segs.append((ch, colr))
            while segs and not segs[-1][0].strip():
                segs.pop()
            if segs:
                last, col = segs[-1]
                segs[-1] = (last.rstrip(), col)
            out.append(segs)
        return out


def line_pts(x0, y0, x1, y1):
    n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
    return [(x0 + (x1 - x0) * i / max(n - 1, 1), y0 + (y1 - y0) * i / max(n - 1, 1)) for i in range(n)]


def curve_pts(fn, x0, x1):
    pts, prev = [], None
    for x in range(x0, x1):
        y = fn(x)
        if prev is not None:
            pts += line_pts(x - 1, prev, x, y)
        prev = y
    return pts


def blocks(v):  # 0..1 → ▁..█
    return " ▁▂▃▄▅▆▇█"[max(0, min(8, int(round(v * 8))))]


def bar(g, r, c, n, frac, color, empty="░"):
    full = int(round(n * max(0, min(1, frac))))
    g.put(r, c, "█" * full, color)
    g.put(r, c + full, empty * (n - full), TERM["dim"])


def with_hold(frames_fn, n, hold=6):
    """Frame 0 = the finished state (index n-1), then the run, then a hold."""
    seq = [frames_fn(i) for i in range(n)]
    return [seq[-1]] + seq[:-1] + [seq[-1]] * hold


# ── OpenTerminalUI: candles, MA, volume, last-price line ──
def scene_candles(cols, rows, acc):
    rnd = _random.Random(11)
    view = cols - 9
    data, price = [], 100.0
    for _ in range(view + 60):
        o = price
        c = o + rnd.gauss(0.08, 0.55)
        h, l = max(o, c) + abs(rnd.gauss(0, .3)), min(o, c) - abs(rnd.gauss(0, .3))
        data.append((o, h, l, c, abs(rnd.gauss(1, .45))))
        price = c
    ch = rows - 4  # chart rows
    def frame(f):
        g = Grid(cols, rows)
        win = data[f: f + view]
        lo, hi = min(d[2] for d in win), max(d[1] for d in win)
        pad = (hi - lo) * .06
        lo, hi = lo - pad, hi + pad
        ysub = lambda v: (hi - v) / (hi - lo) * (ch * 4 - 1)
        last = win[-1]
        o0 = win[0][0]
        chg = (last[3] - o0) / o0 * 100
        up = last[3] >= last[0]
        g.puts(0, 0, ("DEMO/USD", TERM["fg"]), (" · 1m  ", TERM["muted"]),
               ("O ", TERM["muted"]), (f"{last[0]:.2f} ", TERM["fg"]), ("H ", TERM["muted"]), (f"{last[1]:.2f} ", TERM["fg"]),
               ("L ", TERM["muted"]), (f"{last[2]:.2f} ", TERM["fg"]), ("C ", TERM["muted"]),
               (f"{last[3]:.2f} ", TERM["green"] if up else RED), (f"{'▲' if chg >= 0 else '▼'}{abs(chg):.2f}%", TERM["green"] if chg >= 0 else RED))
        for rr in range(1, 1 + ch):  # faint grid
            for cc in range(0, view, 6):
                g.put(rr, cc, "·", TERM["dim"])
        # candles: wick │, body █ (half-cells with ▀ ▄ for finer edges)
        for i, (o, h, l, c, v) in enumerate(win):
            colr = TERM["green"] if c >= o else RED
            top, bot = ysub(max(o, c)) / 4, ysub(min(o, c)) / 4
            for rr in range(int(ysub(h) / 4), int(ysub(l) / 4) + 1):
                g.put(1 + rr, i, "│", colr)
            for rr in range(int(top), int(bot) + 1):
                cell_t, cell_b = max(top, rr), min(bot + .25, rr + 1)
                chx = "█" if cell_b - cell_t > .6 else ("▀" if cell_t - rr < .5 else "▄")
                g.put(1 + rr, i, chx, colr)
        # moving average (braille, behind the candles)
        ma = []
        for i in range(len(win)):
            seg = data[max(0, f + i - 8): f + i + 1]
            ma.append(sum(d[3] for d in seg) / len(seg))
        g.dots(curve_pts(lambda x: ysub(ma[min(len(ma) - 1, x // 2)]), 0, view * 2), TERM["amber"], r0=1)
        # last-price line + axis
        lr = 1 + int(ysub(last[3]) / 4)
        for cc in range(view):
            if g.cell[lr][cc][0] in " ·":
                g.put(lr, cc, "╌", TERM["sky"])
        for k in range(4):
            v = hi - (hi - lo) * k / 3
            g.put(1 + int(k * (ch - 1) / 3), view + 1, f"{v:7.2f}", TERM["muted"])
        g.put(lr, view + 1, f"{last[3]:7.2f}", TERM["bg"] if False else TERM["sky"])
        # volume
        vmax = max(d[4] for d in win)
        for i, d in enumerate(win):
            g.put(1 + ch, i, blocks(d[4] / vmax), "#166534" if d[3] >= d[0] else "#7f1d1d")
        g.puts(rows - 2, 0, ("vol ", TERM["muted"]), ("MA8 ", TERM["amber"]), ("── ", TERM["amber"]),
               ("RSI ", TERM["muted"]), (f"{50 + 30 * math.tanh(chg):.0f}", TERM["fg"]))
        g.puts(rows - 1, 0, ("● ", TERM["green"]), ("paper trading · backtest · screener · alerts", TERM["muted"]))
        return g.rows()
    return [frame(f) for f in range(48)], 9.6


# ── EmbeddedDisplayStudio: an HMI with an arc gauge, trend, buttons, deploy ──
def scene_hmi(cols, rows, acc):
    n = 32
    hist = [60 + 8 * math.sin(i / 5) + 3 * math.sin(i / 1.7) for i in range(200)]
    def frame(f):
        g = Grid(cols, rows)
        w = min(cols, 78)
        g.box(0, 0, rows - 1, w, TERM["dim"], "PANEL-01 · 800×480 · LVGL", acc)
        g.puts(0, w - 26, ("[ MAIN ]", TERM["fg"]), (" SETPOINTS ", TERM["muted"]), (" ALARMS ", TERM["muted"]))
        temp = hist[f * 2 + 30]
        # arc gauge (braille): 0..100 °C over 180°
        gx, gy, R = 24, 22, 18  # sub-pixel centre and radius (braille dots are ~square)
        arc = [(gx + R * math.cos(a), gy - R * math.sin(a)) for a in [math.pi * i / 90 for i in range(91)]]
        arc += [(gx + (R - 2) * math.cos(a), gy - (R - 2) * math.sin(a)) for a in [math.pi * i / 90 for i in range(0, 91, 2)]]
        g.dots([(x, y) for x, y in arc], TERM["dim"], r0=1, c0=2)
        hot = [(x, y) for (x, y), i in zip(arc[:91], range(91)) if i >= 90 * (1 - temp / 100)]
        g.dots(hot, acc, r0=1, c0=2)
        ang = math.pi * (1 - temp / 100)
        g.dots(line_pts(gx, gy, gx + (R - 4) * math.cos(ang), gy - (R - 4) * math.sin(ang)), TERM["fg"], r0=1, c0=2)
        g.puts(7, 9, (f"{temp:5.1f}", TERM["fg"]), (" °C", TERM["muted"]))
        g.puts(8, 4, ("0", TERM["dim"]), ("  TEMP  ", TERM["muted"]), ("100", TERM["dim"]))
        # trend (braille), scrolling
        tx, tw_ = 28, 30
        g.put(1, tx, "TEMP · 60 s", TERM["muted"])
        seg = hist[f * 2: f * 2 + tw_ * 2]
        g.dots(curve_pts(lambda x: (80 - seg[min(len(seg) - 1, x)]) / 30 * 15, 0, tw_ * 2), acc, r0=2, c0=tx)
        g.hline(6, tx, tx + tw_ - 1, TERM["dim"], "┄")
        # flow bar + buttons + lamps
        bx = tx + tw_ + 3
        g.put(1, bx, "FLOW", TERM["muted"])
        fl = .5 + .35 * math.sin(f / 4)
        for i in range(4):
            g.put(5 - i, bx + 1, "██" if fl * 4 > i + .5 else "░░", TERM["green"] if fl * 4 > i + .5 else TERM["dim"])
        g.put(6, bx, f"{fl * 100:3.0f}%", TERM["fg"])
        g.puts(rows - 3, tx, ("[ START ]", TERM["green"]), ("  ", None), ("[ STOP ]", RED))
        g.puts(rows - 3, tx + 21, ("●" if f % 8 < 4 else "○", TERM["green"]), (" RUN  ", TERM["fg"]), ("○", TERM["dim"]), (" FAULT", TERM["muted"]))
        dep = min(1, f / 20) if f else 1
        g.puts(rows - 1, 0, ("❯ ", TERM["green"]), ("deploy ssh panel-01 ", TERM["fg"]))
        bar(g, rows - 1, 22, 14, dep, acc)
        g.put(rows - 1, 37, " ok · atomic swap · rollback armed" if dep >= 1 else " staging bundle…", TERM["green"] if dep >= 1 else TERM["muted"])
        return g.rows()
    return [frame(f) for f in range(n)], 6.4


# ── Noyce IDE: code with a coverage gutter, checks running ──
def scene_checks(cols, rows, acc):
    code = ["int16_t clamp(int16_t v, int16_t lim)", "{", "    if (v > lim)  { return lim; }",
            "    if (v < -lim) { return -lim; }", "    return v;", "}", "", "/* REQ-FCS-112: output bounded */"]
    checks = ["REQ↔code↔test", "MISRA C:2012", "CBMC bounds", "CodeQL", "MC/DC measured", "DO-178C bundle"]
    steps = len(checks) * 3
    def frame(i):
        g = Grid(cols, rows)
        done = i // 3
        cw_ = 46
        g.box(0, 0, rows, cw_, TERM["dim"], "src/fcs/limit.c", TERM["fg"])
        for k, ln in enumerate(code[: rows - 2]):
            covered = done >= 4 or (done >= 2 and k in (0, 2, 4)) or k in (1, 5, 6)
            mark = "█" if covered else "░"
            colr = TERM["green"] if covered else TERM["dim"]
            if ln == "" or ln.startswith("/*"):
                mark, colr = " ", TERM["dim"]
            g.puts(1 + k, 1, (f"{40 + k:3d} ", TERM["dim"]), (mark, colr), (" ", None))
            if ln.startswith("/*"):
                g.put(1 + k, 7, ln[: cw_ - 9], TERM["muted"])
            else:
                import re as _re
                ln = ln[: cw_ - 9]
                g.put(1 + k, 7, ln, TERM["fg"])
                for m in _re.finditer(r"\b(static|if|return|int16_t|lim|v)\b", ln):
                    w_ = m.group(1)
                    colr = TERM["pink"] if w_ in ("static", "if", "return") else TERM["sky"] if w_ == "int16_t" else TERM["amber"]
                    g.put(1 + k, 7 + m.start(), w_, colr)
        x = cw_ + 2
        g.puts(0, x, ("❯ ", TERM["green"]), ("noyce verify", TERM["fg"]))
        for k, ch_ in enumerate(checks):
            if k < done:
                st, sc = "✓", TERM["green"]
            elif k == done:
                st, sc = SPIN[i % len(SPIN)], acc
            else:
                st, sc = "·", TERM["dim"]
            g.puts(1 + k, x, (st + " ", sc), (ch_, TERM["fg"] if k <= done else TERM["muted"]))
        g.put(rows - 2, x, "evidence", TERM["muted"])
        bar(g, rows - 2, x + 9, cols - x - 9, done / len(checks), acc)
        g.put(rows - 1, x, "measured, not claimed", TERM["muted"])
        return g.rows()
    return with_hold(frame, steps + 1, 8), 6.4


# ── WireVoice: a circuit diagram that lights up as the answer is spoken ──
def scene_harness(cols, rows, acc):
    n = 36
    route = [(3, c) for c in range(9, 40)] + [(r, 40) for r in range(3, 5)] + [(4, c) for c in range(40, 56)]  # J1-14 → P3-7
    def frame(f):
        g = Grid(cols, rows)
        # connectors
        g.box(0, 0, 7, 9, TERM["muted"], "J1", TERM["fg"])
        for k, pin in enumerate(("12", "13", "14", "15", "16")):
            g.put(1 + k, 2, f"{pin} ●", acc if pin == "14" else TERM["muted"])
        g.box(2, 56, 5, 9, TERM["muted"], "P3", TERM["fg"])
        for k, pin in enumerate(("6", "7", "8")):
            g.put(3 + k, 58, f"● {pin}", acc if pin == "7" else TERM["muted"])
        # wires (dim), the asked-about route in accent
        # pins 12, 13 and 16 (dim); 13 joins 16 at splice SP1; 16 runs through fuse F2 to P3-8
        g.hline(1, 9, 30, TERM["dim"]); g.put(1, 31, "┐", TERM["dim"]); g.vline(31, 2, 2, TERM["dim"])
        g.hline(2, 9, 25, TERM["dim"]); g.put(2, 26, "┐", TERM["dim"]); g.vline(26, 3, 4, TERM["dim"])
        g.hline(5, 9, 55, TERM["dim"])
        g.put(5, 26, "◆", TERM["amber"]); g.put(6, 25, "SP1", TERM["muted"])   # splice
        g.put(5, 34, "┤F2├", TERM["amber"])                                    # fuse
        # the asked-about wire: J1-14 → P3-7
        g.hline(3, 9, 39, acc); g.put(3, 40, "┐", acc); g.put(4, 40, "└", acc); g.hline(4, 41, 55, acc)
        g.put(3, 12, " 22 AWG · RD/WH ", acc)
        # the travelling signal
        pos = route[(f * 3) % len(route)]
        g.put(pos[0], pos[1], "●", TERM["fg"])
        # voice: question while the signal travels, then the answer
        speaking = f < n // 2
        wr = rows - 4  # three rows of voice, mirrored about the middle
        pts = []
        for x in range(cols * 2):
            env = abs(math.sin(x * .045 + f * .35)) ** 1.5
            a = (0.25 + 5.5 * env * abs(math.sin(x * .23 + f * 1.1))) * (1 if speaking else .85)
            pts += line_pts(x, 6 - a, x, 6 + a)
        g.dots(pts, TERM["pink"] if speaking else acc, r0=wr)
        g.puts(rows - 1, 0, ("» " if speaking else "« ", TERM["pink"] if speaking else acc),
               ("“J1 pin 14 kahaan jaata hai?”" if speaking else "J1-14 → P3-7 · 22 AWG red/white · sheet 4", TERM["fg"]))
        return g.rows()
    return [frame(f) for f in range(n)], 7.2


# ── ARINC 615A: network diagram, packets, TFTP log ──
def scene_arinc(cols, rows, acc):
    log = ["WRQ  FMS_v4.LUR", "OACK blksize=1428", "DATA blk 0001", "ACK  blk 0001", "DATA blk 0412", "ACK  blk 0412",
           "DATA blk 0901", "ACK  blk 0901", "LUS  status 0x0003 · in progress", "LUS  status 0x0001 · accepted"]
    n = 30
    def frame(f):
        g = Grid(cols, rows)
        g.box(0, 0, 4, 15, acc, "LOADER", acc); g.put(1, 2, "a615a ▸ CLI", TERM["fg"]); g.put(2, 2, "ARINC 665", TERM["muted"])
        g.box(0, 25, 3, 8, TERM["muted"], "SW", TERM["fg"])
        g.box(0, 44, 3, 11, TERM["fg"], "FMS-1", TERM["fg"]); g.box(4, 44, 3, 11, TERM["muted"], "DCU-2", TERM["muted"])
        g.hline(1, 15, 24, TERM["dim"]); g.hline(1, 33, 43, TERM["dim"])
        g.put(2, 29, "┬", TERM["muted"]); g.vline(29, 3, 4, TERM["dim"]); g.put(5, 29, "└", TERM["dim"]); g.hline(5, 30, 43, TERM["dim"])
        g.put(1, 56, "LRU", TERM["muted"])
        if f < n - 1:
            for k in range(0, 30, 6):
                p = (k + f * 2) % 30
                if p < 10:
                    g.put(1, 15 + p, "▶", TERM["amber"])
                elif p < 21:
                    g.put(1, 33 + p - 10, "▶", TERM["amber"])
        prog = min(1, f / (n - 1)) if f else 1
        for k in range(3):
            idx = min(len(log) - 1, int(prog * (len(log) - 1)) - 2 + k)
            if idx >= 0:
                g.puts(7 + k, 0, ("tftp ", TERM["dim"]), (log[idx], TERM["fg"] if k == 2 else TERM["muted"]))
        g.put(rows - 1, 0, "FMS_v4", TERM["fg"])
        bar(g, rows - 1, 7, 34, prog, acc)
        g.put(rows - 1, 42, f" {prog * 100:3.0f}% " + ("· verified ✓" if prog >= 1 else "· loading"), TERM["green"] if prog >= 1 else TERM["muted"])
        return g.rows()
    return [frame(n - 1)] + [frame(f) for f in range(n - 1)] + [frame(n - 1)] * 6, 5.4


# ── NETRA debugger: three braille scope channels ──
def scene_scope(cols, rows, acc):
    n = 30
    chans = [("US", TERM["sky"], lambda x, f: math.sin((x + f * 4) * .11) * (.7 + .3 * math.sin((x + f * 4) * .013))),
             ("AX", TERM["green"], lambda x, f: .6 * math.sin((x + f * 4) * .31) + .25 * math.sin((x + f * 4) * 1.3)),
             ("GZ", TERM["amber"], lambda x, f: .8 * math.tanh(3 * math.sin((x + f * 4) * .05)))]
    def frame(f):
        g = Grid(cols, rows)
        h = (rows - 2) // 3
        pw = cols - 14
        for k, (name, colr, fn) in enumerate(chans):
            r0 = k * h
            g.put(r0 + h // 2, 0, name, TERM["muted"])
            for cc in range(3, 3 + pw, 8):
                for rr in range(r0, r0 + h):
                    g.put(rr, cc, "┊" if rr == r0 else " ", TERM["dim"])
            g.dots(curve_pts(lambda x: (1 - fn(x, f)) / 2 * (h * 4 - 2) + 1, 0, pw * 2), colr, r0=r0, c0=3)
            v = fn(pw * 2, f)
            g.put(r0 + h // 2, 3 + pw + 1, f"{v:+.2f}", colr)
        g.puts(rows - 1, 0, ("● ", TERM["green"]), ("100 Hz · obstacle 1.42 m · twin synced", TERM["muted"]))
        return g.rows()
    return [frame(f) for f in range(n)], 3.0


# ── NETRA device: sonar cone and echo ──
def scene_sonar(cols, rows, acc):
    n = 28
    wall = cols - 16
    def frame(f):
        g = Grid(cols, rows)
        g.box(1, 0, 5, 12, acc, "ESP32", acc); g.put(2, 2, "C6", TERM["fg"]); g.put(3, 2, "HC-SR04", TERM["muted"]); g.put(4, 2, "MPU6050", TERM["muted"])
        for rr in range(0, rows - 3):
            g.put(rr, wall, "▓", TERM["amber"])
        cy = 3 * 4 + 2
        phase = ((f + n * .3) % n) / n
        out_r = phase * 2 * (wall - 12) * 2 if phase < .5 else None
        back_r = (phase - .5) * 2 * (wall - 12) * 2 if phase >= .5 else None
        pts = []
        for trail in (0, 5, 10):  # three wavefronts: ")))" outbound, "(((" echo
            if out_r is not None and out_r - trail > 2:
                g.dots([(24 + (out_r - trail) * math.cos(math.radians(a)), cy + (out_r - trail) * math.sin(math.radians(a)))
                        for a in range(-35, 36, 1)], TERM["sky"])
            if back_r is not None and back_r - trail > 2:
                g.dots([((wall * 2) - (back_r - trail) * math.cos(math.radians(a)), cy + (back_r - trail) * math.sin(math.radians(a)))
                        for a in range(-35, 36, 1)], TERM["pink"])
        g.put(rows - 3, 12, "0" + "┄" * (wall - 14) + "142 cm", TERM["muted"])
        g.puts(rows - 2, 0, ("echo ", TERM["muted"]), ("8.27 ms", TERM["fg"]), ("  →  ", TERM["dim"]), ("142 cm", TERM["fg"]), ("   alert ", TERM["muted"]), ("clear", TERM["green"]))
        wob = math.sin(f / 3) * .04
        g.puts(rows - 1, 0, ("imu ", TERM["muted"]), (f"ax {wob:+.2f}  ay {-wob / 2:+.2f}  az +0.98 g", TERM["fg"]))
        return g.rows()
    return [frame(f) for f in range(n)], 2.8


# ── Ornith: tokens streaming, tokenizer-coloured, throughput trace ──
def scene_tokens(cols, rows, acc):
    toks = ("Orn|ith|-|1|.|5| runs| on| one| DGX| Spark|:| NV|FP|4| experts|,| FP|8| attention|,| and| multi|-token| "
            "prediction| drafts| that| are| accepted| most| of| the| time|.| Sixteen| users| share| it| at| 262|K| context|.").split("|")
    width = cols - 2
    def frame(k):
        g = Grid(cols, rows)
        g.puts(0, 0, ("POST ", TERM["green"]), ("/v1/chat/completions", TERM["fg"]), ("  stream=true  model=ornith-1.5", TERM["muted"]))
        r, c = 2, 0
        for i, t_ in enumerate(toks[:k]):
            if c + len(t_) > width:
                r, c = r + 1, 0
                t_ = t_.lstrip()
            if r >= rows - 3:
                break
            g.put(r, c, t_, TERM["fg"] if i % 2 == 0 else "#a5b4fc")
            c += len(t_)
        if k < len(toks):
            g.put(r, c, "▌", acc)
        trace = [300 + 50 * math.sin(i / 3) + 15 * math.sin(i * 1.7) for i in range(cols * 2)]
        tr = curve_pts(lambda x: (400 - trace[min(len(trace) - 1, x + k)]) / 140 * 6, 0, (cols - 24) * 2)
        g.dots(tr + [(x, y + 1) for x, y in tr], acc, r0=rows - 2)
        g.puts(rows - 2, cols - 22, ("351.7", TERM["fg"]), (" tok/s", TERM["muted"]))
        g.puts(rows - 1, cols - 22, ("16 users · MTP ~87%", TERM["muted"]))
        return g.rows()
    return with_hold(frame, len(toks) + 1, 10), 6.0


# ── Qwen3.8: shards quantizing; weight histogram snapping to 4-bit bins ──
def scene_shards(cols, rows, acc):
    shards = rows - 2
    steps = shards * 2
    def frame(i):
        g = Grid(cols, rows)
        g.puts(0, 0, ("❯ ", TERM["green"]), ("quantize --experts nvfp4 --attn fp8 --stream", TERM["fg"]))
        done = i / 2
        for k in range(shards):
            frac = 1 if k < int(done) else (done - int(done) if k == int(done) else 0)
            g.put(1 + k, 0, f"{k + 1:02d}/{shards:02d} ", TERM["muted"])
            bar(g, 1 + k, 6, 18, frac, acc)
            g.put(1 + k, 25, "fp4" if frac >= 1 else ("…" if frac else "bf16"), TERM["green"] if frac >= 1 else TERM["dim"])
        # histogram: smooth (bf16) → 16 spikes (fp4) as quantization proceeds
        hx, hw = 31, cols - 31
        q = min(1, i / steps)
        g.put(1, hx, "weights", TERM["muted"])
        pts = []
        for x in range(hw * 2):
            u = (x / (hw * 2) - .5) * 6
            smooth = math.exp(-u * u / 2)
            bin_ = round((x / (hw * 2)) * 15) / 15
            ub = (bin_ - .5) * 6
            spike = math.exp(-ub * ub / 2) * (1 if abs(x / (hw * 2) - bin_) < .012 else 0)
            v = smooth * (1 - q) + spike * q
            top = (rows - 3) * 4 - v * ((rows - 4) * 4)
            pts += line_pts(x, top, x, (rows - 3) * 4)
        g.dots(pts, acc if q >= 1 else TERM["sky"], r0=2, c0=hx)
        g.put(rows - 1, hx, "bf16 → 16 levels" if q < 1 else "16 levels · data-free ✓", TERM["green"] if q >= 1 else TERM["muted"])
        return g.rows()
    return with_hold(frame, steps + 1, 8), 5.6


# ── Qwen3.6: 12 users decoding at once ──
def scene_users(cols, rows, acc):
    rnd = _random.Random(5)
    users = 12
    sp = [rnd.uniform(.7, 1.3) for _ in range(users)]
    global WORDS
    WORDS = ("each token is routed to its top experts while the shared prefix stays cached so the next "
             "request starts warm and the spark keeps every user moving at once ")
    n = 30
    def frame(f):
        g = Grid(cols, rows)
        per = (users + 1) // 2
        lw = (cols - 2) // 2 - 6
        for u in range(users):
            r, c = 1 + u % per, (u // per) * (lw + 7)
            ln = int((f * sp[u] * 1.4 + u * 5) % (lw + 6))
            g.put(r, c, f"u{u + 1:02d} ", TERM["muted"])
            s = (WORDS[u * 7 % len(WORDS):] + WORDS)[:lw][:ln]
            g.put(r, c + 4, s, TERM["fg"] if u % 3 else acc)
            if ln < lw:
                g.put(r, c + 4 + ln, "▌", acc)
        g.puts(0, 0, ("12 concurrent", TERM["fg"]), (" · 262K ctx · ", TERM["muted"]), ("219 tok/s peak", acc))
        g.put(rows - 2, 0, "KV  ", TERM["muted"]); bar(g, rows - 2, 4, 20, .62 + .1 * math.sin(f / 5), TERM["sky"])
        g.puts(rows - 2, 26, ("prefix hits ", TERM["muted"]), ("5.1× faster", acc))
        g.puts(rows - 1, 0, ("prometheus ", TERM["muted"]), ("▸ ", TERM["dim"]), ("grafana ", TERM["muted"]), ("▸ ", TERM["dim"]), ("dcgm", TERM["muted"]))
        return g.rows()
    return [frame(f) for f in range(n)], 4.5


# ── OpenTokenMonitor: smooth braille usage curves per tool ──
def scene_usage(cols, rows, acc):
    tools = [("claude", "#d97757", .21), ("codex ", TERM["fg"], .33), ("gemini", TERM["sky"], .27)]
    n = 30
    def frame(f):
        g = Grid(cols, rows)
        g.puts(0, 0, ("● ", TERM["green"]), ("local only · nothing leaves this machine", TERM["muted"]))
        h = (rows - 2) // 3
        pw = cols - 26
        for k, (name, colr, fq) in enumerate(tools):
            r0 = 1 + k * h
            g.put(r0 + h // 2, 0, name, colr)
            fn = lambda x: .5 + .35 * math.sin((x + f * 3) * fq * .3 + k) + .15 * math.sin((x + f * 3) * fq)
            curve = curve_pts(lambda x: (1 - fn(x)) * (h * 4 - 2), 0, pw * 2)
            g.dots(curve + [(x, y + 1) for x, y in curve], colr, r0=r0, c0=7)
            q = .45 + .25 * math.sin(f / 6 + k * 2)
            g.put(r0 + h // 2, 8 + pw, "quota ", TERM["muted"]); bar(g, r0 + h // 2, 14 + pw, 10, q, colr)
        g.puts(rows - 1, 0, ("today ", TERM["muted"]), ("trend ↗", TERM["fg"]), ("  · resets in 3h 12m", TERM["muted"]))
        return g.rows()
    return [frame(f) for f in range(n)], 5.0


# ── Skanda card: the MRI in fine ASCII, outline drawing row by row ──
def scene_skanda(cols, rows, acc):
    mc = min(cols - 22, 44)
    base, mask = mri_ascii(cols=mc, rows=rows)
    def frame(upto):
        g = Grid(cols, rows)
        for r in range(rows):
            b = base[r] if r < len(base) else ""
            m = mask[r] if r < len(mask) else ""
            for c in range(max(len(b), len(m))):
                if r < upto and c < len(m) and m[c] != " ":
                    g.put(r, c, m[c], acc)
                elif c < len(b) and b[c] != " ":
                    g.put(r, c, b[c], TERM["muted"])
        x = mc + 2
        g.puts(1, x, ("❯ ", TERM["green"]), ("read MRI", TERM["fg"]))
        g.puts(3, x, ("oedema", TERM["fg"]), (" [SEG]", TERM["pink"]))
        g.puts(4, x, ("tumour", TERM["fg"]), (" [SEG]", TERM["pink"]))
        g.puts(5, x, ("enhancing", TERM["fg"]), (" [SEG]", TERM["pink"]))
        g.puts(7, x, ("IoU ", TERM["muted"]), ("0.97", TERM["fg"]))
        g.puts(8, x, ("MedGemma ", TERM["muted"]), ("0.24", TERM["muted"]))
        return g.rows()
    return with_hold(lambda u: frame(u), rows + 1, 10), 4.4


SCENES = {"openterminalui": scene_candles, "eds": scene_hmi, "noyce": scene_checks, "wirevoice": scene_harness,
          "arinc": scene_arinc, "netra-debugger": scene_scope, "netra-device": scene_sonar, "ornith": scene_tokens,
          "qwen38": scene_shards, "qwen36": scene_users, "opentokenmonitor": scene_usage, "skanda": scene_skanda}


def mono_row(x, y, size, segs, extra="", cls=None):
    """One row of ASCII, pinned to an exact monospace width so every font (and
    braille glyphs from fallback fonts) lines up on the same grid."""
    segs = [(s_, c) for s_, c in segs if s_]
    n = sum(len(s_) for s_, _ in segs)
    if not n or not "".join(s_ for s_, _ in segs).strip():
        return ""
    body = "".join(f'<tspan fill="{c}">{escape(s_)}</tspan>' for s_, c in segs)
    font = f'class="{cls}"' if cls else f'font-family="{MONO}" font-size="{size}"'
    return (f'<text x="{x}" y="{y:.1f}" {font} xml:space="preserve" '
            f'textLength="{n * size * .6:.0f}" lengthAdjust="spacingAndGlyphs"{extra}>{body}</text>')


def ascii_panel(t, key, p, x, y, w, h, size=11):
    """A dark terminal inset inside a card, playing the project's scene."""
    lh = size * 1.22
    cols, rows = int((w - 28) / (size * .6)), int((h - 34) / lh)
    frames, period = SCENES[key](cols, rows, p["accent"])
    out = (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{TERM["bg"]}" stroke="{t["border"]}"/>'
           f'<circle cx="{x + 16}" cy="{y + 14}" r="3.5" fill="#3f3f46"/><circle cx="{x + 28}" cy="{y + 14}" r="3.5" fill="#3f3f46"/>'
           f'<circle cx="{x + 40}" cy="{y + 14}" r="3.5" fill="#3f3f46"/>'
           f'<text x="{x + w - 14}" y="{y + 18}" text-anchor="end" font-family="{MONO}" font-size="10" fill="{TERM["muted"]}">~/{escape(p["repo"] or key).lower()}</text>')
    n = len(frames)
    name = f"fb{n}x{int(period * 100)}"
    out += (f'<style>@keyframes {name}{{0%{{opacity:1}}{100 / n - .005:.3f}%,100%{{opacity:0}}}}'
            f'.{name}{{animation:{name} {period}s steps(1,end) infinite}}'
            f'.m{{font-family:{MONO};font-size:{size}px}}</style>')
    top = y + 34 + size
    for k, fr in enumerate(frames):
        out += f'<g class="{name}" style="animation-delay:{-k * period / n:.3f}s"' + ('' if k == 0 else ' opacity="0"') + '>'
        for r, segs in enumerate(fr[:rows]):
            out += mono_row(x + 14, top + r * lh, size, segs, cls="m")
        out += '</g>'
    return out


# ── main ─────────────────────────────────────────────────────────────────────

WIDE = {"skanda", "noyce", "wirevoice", "openterminalui", "arinc", "ornith"}
SLUGS = {"train": "skanda", "now": "building", "award": "recognition", "oss": "open-source", "mlops": "inference"}
HEADINGS = {
    "about": ("About", "Aerospace, embedded systems, developer tools, applied AI and model training."),
    "train": ("Custom model training", "Skanda: a 31B vision-language model, fine-tuned end to end on one DGX Spark."),
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
            f"hero-{theme}.svg": ascii_hero(t, theme),
            f"skanda-terminal-{theme}.svg": skanda_terminal(t, theme),
            f"bento-{theme}.svg": bento(t, theme),
            f"inference-{theme}.svg": inference(t, theme),
            f"stack-{theme}.svg": stack(t, theme),
            f"footer-{theme}.svg": footer(t, theme),
            f"skanda-bench-{theme}.svg": skanda_bench(t, theme),
            f"skanda-reads-{theme}.svg": skanda_reads(t, theme),
        }
        for k, p in PROJECTS.items():
            files[f"card-{k}-{theme}.svg"] = card(k, p, t, theme, counts, k in WIDE)
        for k, (a, b) in HEADINGS.items():
            files[f"h-{k}-{theme}.svg"] = heading(t, a, b, theme, SLUGS.get(k, k))
        for k in ("github", "site", "x", "web", "repos"):
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
