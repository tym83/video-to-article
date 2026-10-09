#!/usr/bin/env python3
"""Stage 1: get the source video (YouTube/any yt-dlp URL or a local file) into a work folder.

Usage:
    fetch.py <url-or-path> [--workdir DIR]

Creates <workdir>/<id>/01-source/ with:
    video.<ext>      the video (kept for frame extraction)
    audio.wav        16 kHz mono audio for Whisper
    source.json      normalised metadata: id, title, url, duration, upload_date, channel, chapters, description
Prints the work folder path on the last line.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, text=True, **kw)


def slugify(text, limit=48):
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE).strip().lower()
    return re.sub(r"[\s_-]+", "-", text)[:limit].strip("-") or "video"


def probe_duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True)
    try:
        return float(out.stdout.strip())
    except ValueError:
        return None


def extract_audio(video, wav):
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000", str(wav)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"could not extract audio from {video.name} (no audio stream?): {r.stderr.strip()[:300]}")


def from_url(url, workdir):
    info = json.loads(run(["yt-dlp", "--dump-single-json", "--no-playlist", url], capture_output=True).stdout)
    vid = info.get("id") or hashlib.sha1(url.encode()).hexdigest()[:11]
    root = Path(workdir) / vid
    src = root / "01-source"
    src.mkdir(parents=True, exist_ok=True)
    run(["yt-dlp", "--no-playlist", "-f", "bv*[height<=1080]+ba/b[height<=1080]/b", "--merge-output-format", "mp4",
         "--write-thumbnail", "--convert-thumbnails", "jpg", "-o", str(src / "video.%(ext)s"), url])
    video = next((p for p in src.iterdir() if p.stem == "video" and p.suffix not in (".jpg", ".webp", ".png", ".json", ".part")), None)
    if video is None:
        sys.exit("yt-dlp did not produce a media file")
    (src / "info.json").write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")
    meta = {
        "id": vid,
        "kind": "url",
        "url": info.get("webpage_url") or url,
        "title": info.get("title"),
        "channel": info.get("channel") or info.get("uploader"),
        "upload_date": info.get("upload_date"),
        "duration": info.get("duration") or probe_duration(video),
        "description": info.get("description"),
        "chapters": info.get("chapters") or [],
        "video": video.name,
        "thumbnail": "video.jpg" if (src / "video.jpg").exists() else None,
    }
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=codec_type",
                            "-of", "csv=p=0", str(video)], capture_output=True, text=True).stdout
    meta["has_video"] = "video" in probe
    return root, video, meta


def from_file(path, workdir):
    path = Path(path).expanduser().resolve()
    if not path.is_file():
        sys.exit(f"{path}: no such file (for a link, include https://)")
    vid = f"{slugify(path.stem)}-{hashlib.sha1(str(path).encode()).hexdigest()[:6]}"
    root = Path(workdir) / vid
    src = root / "01-source"
    src.mkdir(parents=True, exist_ok=True)
    video = src / f"video{path.suffix.lower()}"
    if not video.exists():
        try:
            os.link(path, video)
        except OSError:
            shutil.copy2(path, video)
    meta = {
        "id": vid,
        "kind": "file",
        "url": None,
        "source_path": str(path),
        "title": path.stem,
        "channel": None,
        "upload_date": None,
        "duration": probe_duration(video),
        "description": None,
        "chapters": [],
        "video": video.name,
        "thumbnail": None,
    }
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=codec_type",
                            "-of", "csv=p=0", str(video)], capture_output=True, text=True).stdout
    meta["has_video"] = "video" in probe
    return root, video, meta


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", help="video URL (anything yt-dlp supports) or a local video/audio file")
    ap.add_argument("--workdir", default="video-to-article", help="parent folder for per-video work folders")
    a = ap.parse_args()
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            sys.exit(f"{tool} not found: install ffmpeg first")
    source = a.source
    if not re.match(r"^https?://", source) and not Path(source).expanduser().exists() \
            and re.match(r"^(www\.)?[\w-]+(\.[\w-]+)+/", source):
        source = "https://" + source              # youtu.be/abc, www.youtube.com/watch?v=…
    a.source = source
    is_url = re.match(r"^https?://", a.source) is not None
    if is_url and not shutil.which("yt-dlp"):
        sys.exit("yt-dlp not found: pip install -U yt-dlp")
    root, video, meta = (from_url if is_url else from_file)(a.source, a.workdir)
    wav = root / "01-source" / "audio.wav"
    if not wav.exists() or wav.stat().st_mtime < video.stat().st_mtime:
        extract_audio(video, wav)
    (root / "01-source" / "source.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"title: {meta['title']}")
    print(f"duration: {meta['duration']}")
    print(f"has video: {meta['has_video']}")
    print(root)


if __name__ == "__main__":
    main()
