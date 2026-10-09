#!/usr/bin/env python3
"""Guard against summarising: compare the size of every processed chunk with its source.

Usage:
    coverage.py <workfolder> [--article FILE] [--mode clean|translate] [--to ru]

Reads 03-chunks/*.txt (source) and 04-text/NN.md (processed) and writes coverage.md with the length ratio of
each chunk. Spoken filler goes away in a clean-up, and Russian runs longer than English, so the expected
ranges are:
    clean                0.60–1.30
    translate → ru/uk/be 0.85–1.60
    translate → other    0.70–1.50
A chunk below the range was probably summarised and should be redone; above it, padded. With --article the
whole article (markup, comments and special blocks stripped) is compared with the full transcript as well.
Mode and target language are read from the `## Job` section of _context.md when not given.
Exit code 2 when something is out of range.
"""
import argparse
import re
import sys
from pathlib import Path

RANGES = {"clean": (0.60, 1.30), "slavic": (0.85, 1.60), "other": (0.70, 1.50)}


def plain(md):
    md = re.sub(r"(?s)<!--.*?-->", "", md)
    md = re.sub(r"(?m)^> [A-Z_]+:.*$", "", md)                 # special-block lines
    md = re.sub(r"(?m)^#+ ", "", md)
    md = re.sub(r"\*\*[^*\n]{1,60}:\*\*", "", md)              # **Name:** speaker labels
    md = re.sub(r"[*_`>#\[\]]", "", md)
    return re.sub(r"\s+", " ", md).strip()


def source_text(txt):
    return re.sub(r"\s+", " ", re.sub(r"(?m)^\[\d\d:\d\d:\d\d\] ", "", txt)).strip()


def job(root):
    ctx = root / "_context.md"
    if not ctx.exists():
        return None, None
    t = ctx.read_text(encoding="utf-8")
    sec = t.split("## Job", 1)[1].split("\n## ", 1)[0] if "## Job" in t else ""
    mode = "translate" if re.search(r"translat", sec, re.I) else ("clean" if sec else None)
    to = re.search(r"(?:→|->|output language:?\s*)\s*([a-z]{2})\b", sec, re.I)
    return mode, (to.group(1).lower() if to else None)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("workfolder")
    ap.add_argument("--article")
    ap.add_argument("--mode", choices=["clean", "translate"])
    ap.add_argument("--to")
    a = ap.parse_args()
    root = Path(a.workfolder)
    jm, jt = job(root)
    mode, to = a.mode or jm or "clean", (a.to or jt or "ru")
    key = "clean" if mode == "clean" else ("slavic" if to in ("ru", "uk", "be") else "other")
    lo, hi = RANGES[key]

    rows, bad = [], 0
    src_total = out_total = 0
    for src in sorted((root / "03-chunks").glob("*.txt")):
        n = src.name[:2]
        s = len(source_text(src.read_text(encoding="utf-8")))
        dst = root / "04-text" / f"{n}.md"
        o = len(plain(dst.read_text(encoding="utf-8"))) if dst.exists() else 0
        src_total += s
        out_total += o
        r = o / s if s else 0
        flag = "missing" if not dst.exists() else ("TOO SHORT — redo" if r < lo else ("too long — check" if r > hi else "ok"))
        bad += flag != "ok"
        rows.append(f"| {n} | {s} | {o} | {r:.2f} | {flag} |")
    lines = ["# Coverage", "", f"Mode: {mode}" + (f" → {to}" if mode == "translate" else "") + f" · expected ratio {lo:.2f}–{hi:.2f}", "",
             "| chunk | source chars | output chars | ratio | verdict |", "|---|---|---|---|---|", *rows, ""]
    total = out_total / src_total if src_total else 0
    lines.append(f"Chunks total: {out_total} / {src_total} = {total:.2f}")
    if a.article:
        t = len(source_text("\n".join(p.read_text(encoding="utf-8") for p in sorted((root / "03-chunks").glob("*.txt")))))
        art = len(plain(Path(a.article).read_text(encoding="utf-8")))
        ra = art / t if t else 0
        verdict = "ok" if lo * 0.9 <= ra <= hi * 1.1 else "OUT OF RANGE"
        bad += verdict != "ok"
        lines.append(f"Article: {art} / {t} = {ra:.2f} — {verdict}")
    (root / "coverage.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"coverage: {len(rows)} chunks, {bad} flagged, total ratio {total:.2f} (expected {lo:.2f}–{hi:.2f})")
    return 2 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
