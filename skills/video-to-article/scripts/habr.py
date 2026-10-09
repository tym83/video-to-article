#!/usr/bin/env python3
"""Convert the final article to Habr's markdown flavour.

Usage:
    habr.py <article.md> [-o article.habr.md] [--images-base URL] [--cut]

Habr's editor treats markdown headings one level higher than usual, so:
  * the article title is NOT a heading: it is printed as plain text on the first line
    (paste it into Habr's separate title field);
  * '## Section' becomes '# Section', '### Sub' becomes '## Sub', and so on.
Front matter and HTML comments are dropped. Special blocks become plain markdown:
FACTOID / PULLQUOTE / NOTE → blockquotes, IMAGE → ![alt](path) with an italic caption line, CTA → a line with a link.
Code blocks are never touched. With --images-base the local frame paths are rewritten to that URL prefix
(upload the frames first). With --cut a <cut /> tag is placed after the lead paragraph. With --cards DIR (made by `blocks.py … cards`)
FACTOID / PULLQUOTE / NOTE are replaced by their PNG cards — Habr has no callout blocks; the cards must be
uploaded to Habr like the frames (or use --images-base).
"""
import json
import argparse
import re
import sys
from pathlib import Path

KINDS = ("IMAGE", "PULLQUOTE", "FACTOID", "NOTE", "CTA")
FIELD = re.compile(r"^>[ \t]*([A-Z_]+):[ \t]?(.*)$")


def front_matter(text):
    m = re.match(r"(?s)\A---\n(.*?)\n---\n", text)
    if not m:
        return {}, text
    fm = dict(re.findall(r'^(\w+):[ \t]*"?(.*?)"?[ \t]*$', m.group(1), re.M))
    return fm, text[m.end():]


def split_fences(text):
    """[(is_code, chunk)] — fenced code blocks are kept verbatim."""
    parts, buf, code = [], [], False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            if not code:
                parts.append((False, "\n".join(buf)))
                buf = [line]
                code = True
            else:
                buf.append(line)
                parts.append((True, "\n".join(buf)))
                buf = []
                code = False
            continue
        buf.append(line)
    parts.append((code, "\n".join(buf)))
    return parts


def render_block(kind, header, fields, images_base):
    f = {k: " ".join(v).strip() for k, v in fields.items()}
    if kind == "IMAGE":
        src = f.get("SRC") or f.get("FILE") or f"frames/{f.get('ID', 'image')}.jpg"
        if images_base:
            src = images_base.rstrip("/") + "/" + Path(src).name
        cap = f.get("CAPTION")
        return [f"![{f.get('ALT', '')}]({src})"] + ([f"*{cap}*"] if cap else [])
    if kind == "PULLQUOTE":
        who = f.get("ATTRIBUTION")
        return [f"> {f.get('TEXT', '')}"] + ([">", f"> — {who}"] if who else [])
    if kind == "FACTOID":
        num = f.get("NUMBER")
        return [f"> **{num}** {f.get('TEXT', '')}" if num else f"> {f.get('TEXT', '')}"]
    if kind == "NOTE":
        return ([f"> **{header}**"] if header else []) + [f"> {f.get('TEXT', '')}"]
    if kind == "CTA":
        return [f"**{f.get('TITLE', '')}** {f.get('TEXT', '')} [{f.get('BUTTON', 'Подробнее')}]({f.get('HREF', '')})"]
    return []


CARD_KINDS = ("FACTOID", "PULLQUOTE", "NOTE")


def convert_blocks(text, images_base, cards=None, counter=None):
    out, lines, i = [], text.split("\n"), 0
    counter = counter if counter is not None else [0]
    while i < len(lines):
        m = re.match(r"^> (" + "|".join(KINDS) + r"):[ \t]*(.*)$", lines[i])
        if not m:
            out.append(lines[i])
            i += 1
            continue
        kind, header, fields, last = m.group(1), m.group(2).strip(), {}, None
        i += 1
        while i < len(lines) and lines[i].startswith(">") and not re.match(r"^> (" + "|".join(KINDS) + r"):", lines[i]):
            fm = FIELD.match(lines[i])
            if fm:
                last = fm.group(1)
                fields.setdefault(last, []).append(fm.group(2))
            elif last:                       # a wrapped continuation of the previous field
                fields[last].append(lines[i].lstrip("> ").strip())
            i += 1
        if cards is not None and kind in CARD_KINDS:
            card = cards[counter[0]] if counter[0] < len(cards) else None
            counter[0] += 1
            if card:
                src = card["src"]
                if images_base:
                    src = images_base.rstrip("/") + "/" + Path(src).name
                out += [f"![{card['alt']}]({src})", ""]
                continue
        out += render_block(kind, header, fields, images_base) + [""]
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("article")
    ap.add_argument("-o", "--output")
    ap.add_argument("--images-base", help="URL prefix for uploaded frames")
    ap.add_argument("--cut", action="store_true", help="insert <cut /> after the lead paragraph")
    ap.add_argument("--cards", help="folder with cards.json from blocks.py: use PNG cards for FACTOID/PULLQUOTE/NOTE")
    a = ap.parse_args()
    src = Path(a.article)
    fm, body = front_matter(src.read_text(encoding="utf-8"))
    title = fm.get("title")
    cards = None
    if a.cards:
        idx = json.loads((Path(a.cards) / "cards.json").read_text(encoding="utf-8"))
        cards = [dict(c, src=str(Path(a.cards).name + "/" + c["file"])) for c in idx]
    counter = [0]
    parts, seen_h1 = [], False
    for code, chunk in split_fences(body):
        if code:
            parts.append(chunk)
            continue
        chunk = re.sub(r"(?s)<!--.*?-->\n?", "", chunk)
        if not seen_h1:
            h1 = re.search(r"^# (.+)$", chunk, re.M)
            if h1:  # an H1 in the body is the title too: never keep it as a heading
                title = title or h1.group(1).strip()
                chunk = chunk[:h1.start()] + chunk[h1.end():]
                seen_h1 = True
        chunk = convert_blocks(chunk, a.images_base, cards, counter)
        chunk = re.sub(r"^(#{2,6}) ", lambda m: "#" * (len(m.group(1)) - 1) + " ", chunk, flags=re.M)
        parts.append(chunk)
    body = re.sub(r"\n{3,}", "\n\n", "\n".join(parts)).strip() + "\n"
    if a.cut:
        paras = body.split("\n\n")
        lead = next((k for k, p in enumerate(paras) if p.strip() and not p.lstrip().startswith(("#", "!", ">", "```"))), 0)
        paras.insert(lead + 1, "<cut />")
        body = "\n\n".join(paras)
    out = (f"{title}\n\n" if title else "") + body
    dst = Path(a.output) if a.output else src.with_name(src.stem + ".habr.md")
    dst.write_text(out, encoding="utf-8")
    heads = sum(1 for code, ch in split_fences(out) if not code for _ in re.finditer(r"^#+ ", ch, re.M))
    print(f"{dst} · title as plain text: {bool(title)} · headings: {heads} (top level '# ')")


if __name__ == "__main__":
    sys.exit(main())
