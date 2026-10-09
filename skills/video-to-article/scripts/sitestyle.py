#!/usr/bin/env python3
"""Extract a site's visual style (colours, fonts, corner radius) to style the article's special blocks.

Usage:
    sitestyle.py <site-url> [-o style.json]

Downloads the page and up to 8 linked stylesheets (same and third-party hosts), then collects:
  * CSS custom properties whose names look like colours (--primary, --accent, --bg, --text, …);
  * the most used colours in the CSS, split into dark / light / saturated;
  * font families of body and headings, and Google Fonts families linked from the page;
  * the most common border-radius.
Writes a style.json the orchestrator shows to the user for confirmation. It is a heuristic: the user (or the
agent, after a look at the site) can correct any field by hand.
"""
import argparse
import colorsys
import json
import re
import sys
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
NAMED = {"white": "#ffffff", "black": "#000000"}


def get(url, limit=3_000_000):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        data = r.read(limit)
        enc = r.headers.get_content_charset() or "utf-8"
    return data.decode(enc, errors="replace")


def norm_hex(c):
    c = c.lower()
    if c in NAMED:
        return NAMED[c]
    m = re.fullmatch(r"#([0-9a-f]{3})", c)
    if m:
        return "#" + "".join(ch * 2 for ch in m.group(1))
    m = re.fullmatch(r"#([0-9a-f]{6})(?:[0-9a-f]{2})?", c)
    if m:
        return "#" + m.group(1)
    m = re.fullmatch(r"rgba?\(\s*(\d+)[ ,]+(\d+)[ ,]+(\d+)(?:[ ,/]+([\d.]+%?))?\s*\)", c)
    if m:
        a = m.group(4)
        if a and (a.endswith("%") and float(a[:-1]) < 50 or not a.endswith("%") and float(a) < 0.5):
            return None
        return "#%02x%02x%02x" % tuple(min(255, int(x)) for x in m.groups()[:3])
    return None


def hls(hexc):
    r, g, b = (int(hexc[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return colorsys.rgb_to_hls(r, g, b)


def first_family(decl):
    for fam in decl.split(","):
        fam = fam.strip().strip("'\"")
        if fam and not fam.startswith("var(") and fam.lower() not in ("inherit", "initial", "sans-serif", "serif",
                                                                         "monospace", "system-ui", "-apple-system"):
            return fam
    return None


def analyse(url):
    html = get(url)
    css_links = re.findall(r"<link[^>]+rel=[\"']?stylesheet[^>]*>", html, re.I)
    hrefs = [re.search(r"href=[\"']?([^\"' >]+)", l).group(1) for l in css_links if re.search(r"href=", l)]
    css = "\n".join(re.findall(r"(?s)<style[^>]*>(.*?)</style>", html, re.I))
    for h in hrefs[:8]:
        try:
            css += "\n" + get(urllib.parse.urljoin(url, h))
        except Exception:
            pass
    google = sorted({urllib.parse.unquote(f).split(":")[0].replace("+", " ")
                     for h in hrefs if "fonts.googleapis.com" in h
                     for f in re.findall(r"family=([^&]+)", h)})
    for imp in re.findall(r"@import\s+url\([\"']?([^)\"']*fonts\.googleapis\.com[^)\"']*)", css):
        google += [urllib.parse.unquote(f).split(":")[0].replace("+", " ") for f in re.findall(r"family=([^&]+)", imp)]

    variables = {}
    for name, val in re.findall(r"--([\w-]+)\s*:\s*([^;}{]+)", css):
        h = norm_hex(val.strip())
        if h and re.search(r"color|primary|accent|brand|bg|background|text|fg|link|main|secondary|highlight", name, re.I):
            variables.setdefault(name, h)

    colours = Counter(h for h in (norm_hex(c) for c in re.findall(r"#[0-9a-fA-F]{3,8}\b|rgba?\([^)]*\)", css)) if h)
    dark = [c for c, _ in colours.most_common() if hls(c)[1] < 0.25]
    light = [c for c, _ in colours.most_common() if hls(c)[1] > 0.92]
    sat = [c for c, _ in colours.most_common() if hls(c)[2] > 0.45 and 0.25 < hls(c)[1] < 0.75]

    def var_like(*keys):
        for k, v in variables.items():
            if any(x in k.lower() for x in keys):
                return v
        return None

    body_font = head_font = None
    for sel, decl in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        fam = re.search(r"font-family\s*:\s*([^;]+)", decl)
        if not fam:
            continue
        f = first_family(fam.group(1))
        f = f.title() if f and f.islower() else f
        if not f:
            continue
        if re.search(r"(^|[\s,])(body|html|:root)([\s,{]|$)", sel) and not body_font:
            body_font = f
        if re.search(r"(^|[\s,])h[12]([\s,{.:]|$)", sel) and not head_font:
            head_font = f
    radii = Counter(r for r in re.findall(r"border-radius\s*:\s*(\d+)px", css) if 0 < int(r) <= 32)  # pills are buttons

    style = {
        "site": url,
        "background": var_like("bg", "background") or (light[0] if light else "#ffffff"),
        "text": var_like("text", "fg", "foreground") or (dark[0] if dark else "#1a1a1a"),
        "accent": var_like("primary", "accent", "brand", "link", "highlight") or (sat[0] if sat else "#3366cc"),
        "muted": (light[1] if len(light) > 1 else "#f4f4f6"),
        "font_body": body_font or (google[0] if google else None),
        "font_heading": head_font or (google[-1] if google else None),
        "google_fonts": sorted(set(google)),
        "radius": int(radii.most_common(1)[0][0]) if radii else 8,
        "css_variables": dict(list(variables.items())[:20]),
        "top_colours": [c for c, _ in colours.most_common(12)],
    }
    return style


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url")
    ap.add_argument("-o", "--output", default="style.json")
    a = ap.parse_args()
    url = a.url if re.match(r"^https?://", a.url) else "https://" + a.url
    try:
        style = analyse(url)
    except Exception as e:
        sys.exit(f"could not read {url}: {e}")
    Path(a.output).write_text(json.dumps(style, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"background {style['background']} · text {style['text']} · accent {style['accent']} · "
          f"fonts {style['font_heading']} / {style['font_body']} · radius {style['radius']}px → {a.output}")


if __name__ == "__main__":
    main()
