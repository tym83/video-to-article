#!/usr/bin/env python3
"""Stage 3: split the transcript into chunks of at most N characters, cutting only at natural pauses.

Usage:
    chunk.py <workfolder> [--max-chars 2500] [--pause 1.2]

A chunk this size is small enough that a model translates or edits it whole instead of summarising it.
Once a chunk is 60 % full it is cut at the first pause of at least --pause seconds; otherwise it is cut before
the segment that would exceed the limit. Cuts never happen inside a Whisper segment (a single very long segment
can therefore exceed the limit). The character count excludes the [HH:MM:SS] line prefixes.

Writes 03-chunks/NN_HH-MM-SS_HH-MM-SS.txt and 03-chunks/manifest.json.
"""
import argparse
import json
import sys
from pathlib import Path


def ts(t):
    t = int(t)
    return f"{t // 3600:02d}:{t % 3600 // 60:02d}:{t % 60:02d}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("workfolder")
    ap.add_argument("--max-chars", type=int, default=2500)
    ap.add_argument("--pause", type=float, default=1.2, help="preferred minimum pause (seconds) for a cut")
    a = ap.parse_args()
    root = Path(a.workfolder)
    segs = [s for s in json.loads((root / "02-transcript" / "transcript.json").read_text(encoding="utf-8"))["segments"]
            if s["text"].strip()]
    if not segs:
        sys.exit("the transcript is empty (silence, music only, or VAD removed everything): nothing to chunk")
    out = root / "03-chunks"
    out.mkdir(exist_ok=True)
    for old in out.glob("*.txt"):
        old.unlink()

    chunks, cur = [], []
    for i, s in enumerate(segs):
        cur.append(s)
        size = sum(len(x["text"]) + 1 for x in cur)
        nxt = segs[i + 1] if i + 1 < len(segs) else None
        gap = (nxt["start"] - s["end"]) if nxt else 99
        # cut at a real pause once the chunk is reasonably full, or hard-cut at the limit
        if nxt is None or (size > a.max_chars * 0.6 and gap >= a.pause) or size + len(nxt["text"]) > a.max_chars:
            chunks.append(cur)
            cur = []

    manifest = []
    for n, ch in enumerate(chunks):
        start, end = ch[0]["start"], ch[-1]["end"]
        name = f"{n:02d}_{ts(start).replace(':', '-')}_{ts(end).replace(':', '-')}.txt"
        text = "\n".join(f"[{ts(s['start'])}] {s['text']}" for s in ch)
        (out / name).write_text(text + "\n", encoding="utf-8")
        manifest.append({"index": n, "file": name, "start": start, "end": end, "start_ts": ts(start), "end_ts": ts(end),
                         "chars": sum(len(s["text"]) for s in ch), "segments": len(ch)})
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(chunks)} chunks, max {max((m['chars'] for m in manifest), default=0)} chars")


if __name__ == "__main__":
    main()
