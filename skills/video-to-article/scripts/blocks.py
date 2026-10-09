#!/usr/bin/env python3
"""Render the article's special blocks (FACTOID, PULLQUOTE, NOTE) for a target platform.

Usage:
    blocks.py <article.md> cards [--style style.json] [--out DIR]
        Render every FACTOID / PULLQUOTE / NOTE as a PNG card (1200 px wide, 2x for sharpness) in the
        site's colours and fonts, and write DIR/cards.json (block index → file). habr.py --cards DIR and
        the site export then put the cards in place of the blocks. Use for platforms without callouts.

    blocks.py <article.md> html [--style style.json] [-o article.site.md] [--css blocks.css]
        For your own site with custom layout: replace the blocks with semantic HTML
        (<aside class="va-factoid">, <figure class="va-pullquote">, <aside class="va-note">) and write a
        small stylesheet in the site's colours and fonts. Works only where you can add CSS and the markdown
        renderer passes raw HTML through (Hugo: markup.goldmark.renderer.unsafe = true).

Fonts: the style's Google Fonts are downloaded on first use into ~/.cache/video-to-article/fonts; otherwise
a system font with Cyrillic is used.
"""
import argparse
import html
import json
import re
import sys
import textwrap
import urllib.parse
import urllib.request
from pathlib import Path

KINDS = ("FACTOID", "PULLQUOTE", "NOTE")
FIELD = re.compile(r"^>[ \t]*([A-Z_]+):[ \t]?(.*)$")
DEFAULT_STYLE = {"background": "#ffffff", "text": "#1a1a1a", "accent": "#3366cc", "muted": "#f4f4f6",
                 "font_body": None, "font_heading": None, "radius": 10}
CACHE = Path.home() / ".cache" / "video-to-article" / "fonts"
SYSTEM_FONTS = ["/System/Library/Fonts/Supplemental/Arial Unicode.ttf", "/Library/Fonts/Arial Unicode.ttf",
                "/System/Library/Fonts/Supplemental/Arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/TTF/DejaVuSans.ttf", "C:/Windows/Fonts/arial.ttf"]


# ---------------------------------------------------------------- parsing
def parse_blocks(text):
    """[(start_line, end_line, kind, header, fields)] for FACTOID/PULLQUOTE/NOTE, outside code fences."""
    lines, out, i, code = text.split("\n"), [], 0, False
    while i < len(lines):
        if lines[i].lstrip().startswith("```"):
            code = not code
        m = None if code else re.match(r"^> (" + "|".join(KINDS) + r"):[ \t]*(.*)$", lines[i])
        if not m:
            i += 1
            continue
        start, kind, header, fields, last = i, m.group(1), m.group(2).strip(), {}, None
        i += 1
        while i < len(lines) and lines[i].startswith(">") \
                and not re.match(r"^> (" + "|".join(KINDS + ("IMAGE", "CTA")) + r"):", lines[i]):
            fm = FIELD.match(lines[i])
            if fm:
                last = fm.group(1)
                fields.setdefault(last, []).append(fm.group(2))
            elif last:
                fields[last].append(lines[i].lstrip("> ").strip())
            i += 1
        out.append((start, i, kind, header, {k: " ".join(v).strip() for k, v in fields.items()}))
    return out


def load_style(path):
    style = dict(DEFAULT_STYLE)
    if path:
        style.update({k: v for k, v in json.loads(Path(path).read_text(encoding="utf-8")).items() if v})
    return style


# ---------------------------------------------------------------- fonts
def google_font(family, weight):
    CACHE.mkdir(parents=True, exist_ok=True)
    dst = CACHE / f"{family.replace(' ', '_')}-{weight}.ttf"
    if dst.exists():
        return str(dst)
    family = family.title() if family.islower() else family
    q = urllib.parse.quote(family) + f":wght@{weight}"
    req = urllib.request.Request(f"https://fonts.googleapis.com/css2?family={q}&subset=cyrillic",
                                 headers={"User-Agent": "Mozilla/4.0"})   # an old UA gets plain TTF urls
    css = urllib.request.urlopen(req, timeout=20).read().decode()
    urls = re.findall(r"url\((https://[^)]+\.ttf)\)", css)
    if not urls:
        raise RuntimeError("no ttf in Google Fonts response")
    dst.write_bytes(urllib.request.urlopen(urls[-1], timeout=30).read())
    return str(dst)


def font_path(family, weight):
    if family:
        try:
            return google_font(family, weight)
        except Exception:
            pass
    for p in SYSTEM_FONTS:
        if Path(p).exists():
            return p
    return None


# ---------------------------------------------------------------- cards
def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def render_card(kind, header, f, style, dst):
    from PIL import Image, ImageDraw, ImageFont
    S = 2
    W = 1200 * S
    pad = 72 * S
    bg, fg, accent, muted = (hex_rgb(style[k]) for k in ("background", "text", "accent", "muted"))
    body_p, head_p = font_path(style.get("font_body"), 400), font_path(style.get("font_heading") or style.get("font_body"), 700)

    def F(path, size):
        return ImageFont.truetype(path, size * S) if path else ImageFont.load_default()

    blocks = []  # (font, text, colour, wrap width in chars, gap after)
    if kind == "FACTOID":
        num = f.get("NUMBER", "")
        if num:
            blocks.append((F(head_p, 120), num, accent, 18, 24))
        blocks.append((F(body_p, 40), f.get("TEXT", ""), fg, 48, 0))
    elif kind == "PULLQUOTE":
        blocks.append((F(head_p, 52), f.get("TEXT", ""), fg, 38, 36))
        if f.get("ATTRIBUTION"):
            blocks.append((F(body_p, 34), "— " + f["ATTRIBUTION"], accent, 60, 0))
    else:  # NOTE
        if header:
            blocks.append((F(head_p, 40), header, accent, 48, 20))
        blocks.append((F(body_p, 36), f.get("TEXT", ""), fg, 56, 0))

    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    laid, h = [], pad
    for font, text, col, width, gap in blocks:
        for line in textwrap.wrap(text, width) or [""]:
            bb = probe.textbbox((0, 0), line, font=font)
            laid.append((pad + (14 * S if kind != "FACTOID" else 0), h, line, font, col))
            h += (bb[3] - bb[1]) + int(font.size * 0.42)
        h += gap * S
    H = h + pad
    card = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(card)
    r = min(int(style.get("radius", 10)), 24) * S
    d.rounded_rectangle([0, 0, W - 1, H - 1], radius=r, fill=muted if kind == "NOTE" else bg,
                        outline=accent if kind == "FACTOID" else None, width=3 * S)
    if kind in ("PULLQUOTE", "NOTE"):
        d.rectangle([pad - 6 * S, pad, pad, H - pad], fill=accent)
    for x, y, line, font, col in laid:
        d.text((x, y), line, font=font, fill=col)
    card.resize((W // S, H // S), Image.LANCZOS).save(dst, optimize=True)


def cmd_cards(article, style, out):
    out.mkdir(parents=True, exist_ok=True)
    text = Path(article).read_text(encoding="utf-8")
    index = []
    for n, (s, e, kind, header, f) in enumerate(parse_blocks(text)):
        name = f"card-{n + 1:02d}-{kind.lower()}.png"
        render_card(kind, header, f, style, out / name)
        alt = " ".join(x for x in (f.get("NUMBER"), header, f.get("TEXT"), f.get("ATTRIBUTION")) if x)
        index.append({"index": n, "kind": kind, "file": name, "alt": alt[:300]})
    (out / "cards.json").write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(index)} cards → {out}/")


# ---------------------------------------------------------------- html for own sites
CSS = """/* video-to-article special blocks — generated from {site} */
.va-factoid, .va-pullquote, .va-note {{ margin: 2em 0; font-family: {body}; color: {text}; }}
.va-factoid {{ border: 2px solid {accent}; border-radius: {r}px; padding: 1.2em 1.5em; background: {bg}; }}
.va-factoid .va-number {{ display: block; font-family: {head}; font-size: 3em; font-weight: 700; line-height: 1.1; color: {accent}; }}
.va-pullquote {{ border-left: 4px solid {accent}; padding: .2em 0 .2em 1.2em; }}
.va-pullquote blockquote {{ margin: 0; font-family: {head}; font-size: 1.5em; line-height: 1.35; font-style: italic; }}
.va-pullquote figcaption {{ margin-top: .6em; color: {accent}; }}
.va-note {{ background: {muted}; border-left: 4px solid {accent}; border-radius: {r}px; padding: 1em 1.3em; }}
.va-note strong {{ display: block; margin-bottom: .3em; color: {accent}; }}
"""


def block_html(kind, header, f):
    e = html.escape
    if kind == "FACTOID":
        num = f'<span class="va-number">{e(f["NUMBER"])}</span>' if f.get("NUMBER") else ""
        return f'<aside class="va-factoid">{num}{e(f.get("TEXT", ""))}</aside>'
    if kind == "PULLQUOTE":
        cap = f'<figcaption>— {e(f["ATTRIBUTION"])}</figcaption>' if f.get("ATTRIBUTION") else ""
        return f'<figure class="va-pullquote"><blockquote>{e(f.get("TEXT", ""))}</blockquote>{cap}</figure>'
    title = f"<strong>{e(header)}</strong>" if header else ""
    return f'<aside class="va-note">{title}{e(f.get("TEXT", ""))}</aside>'


def font_stack(name, fallback):
    return f"'{name}', {fallback}" if name else fallback


def cmd_html(article, style, out_md, out_css):
    text = Path(article).read_text(encoding="utf-8")
    lines = text.split("\n")
    for s, e, kind, header, f in reversed(parse_blocks(text)):
        lines[s:e] = [block_html(kind, header, f)]
    Path(out_md).write_text("\n".join(lines), encoding="utf-8")
    css = CSS.format(site=style.get("site", "defaults"), body=font_stack(style.get("font_body"), "inherit"),
                     head=font_stack(style.get("font_heading") or style.get("font_body"), "inherit"),
                     text=style["text"], accent=style["accent"], bg=style["background"], muted=style["muted"],
                     r=min(int(style.get("radius", 10)), 24))
    if style.get("google_fonts"):
        fams = "&".join("family=" + urllib.parse.quote(x) + ":wght@400;700" for x in style["google_fonts"][:2])
        css = f"@import url('https://fonts.googleapis.com/css2?{fams}&display=swap');\n" + css
    Path(out_css).write_text(css, encoding="utf-8")
    print(f"{out_md} + {out_css}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("article")
    ap.add_argument("mode", choices=["cards", "html"])
    ap.add_argument("--style")
    ap.add_argument("--out", default=None, help="cards: output folder (default: <article dir>/cards)")
    ap.add_argument("-o", "--output", help="html: output markdown (default: article.site.md)")
    ap.add_argument("--css", help="html: stylesheet path (default: blocks.css next to the article)")
    a = ap.parse_args()
    style = load_style(a.style)
    base = Path(a.article).parent
    if a.mode == "cards":
        cmd_cards(a.article, style, Path(a.out) if a.out else base / "cards")
    else:
        cmd_html(a.article, style, a.output or str(Path(a.article).with_name(Path(a.article).stem + ".site.md")),
                 a.css or str(base / "blocks.css"))


if __name__ == "__main__":
    sys.exit(main())
