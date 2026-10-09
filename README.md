# video-to-article

A [Claude Code](https://claude.com/claude-code) plugin that turns a video into a finished, illustrated article.

Give it a YouTube link (or anything `yt-dlp` can download) or a local video/audio file. It transcribes the
speech with Whisper, asks whether to translate and into which language, processes the transcript chunk by
chunk so nothing is summarised away, builds a structured article, fact-checks it against the transcript,
edits it into living literary language, proofreads it, pulls frames from the video and places them in the
text, offers five headlines, and can export the result in Habr's markdown flavour.

Русская версия: [README.ru.md](README.ru.md).

## What you get

```
video-to-article/<video-id>/
├── 01-source/          video, 16 kHz audio, normalised metadata
├── 02-transcript/      transcript.json / .txt / .srt (Whisper, word timestamps)
├── _context.md         speakers, topics, glossary, recognition traps, style guide
├── 03-chunks/          ≤2500-character chunks cut at natural pauses + manifest
├── 04-text/            each chunk translated or cleaned up (five passes)
├── 05-assembled.md     lead, H2/H3 structure, quotes, notes, illustration requests
├── coverage.md         length ratio per chunk: nothing summarised away
├── 05-factcheck.md     PASS/FAIL report against the transcript
├── 06-edited.md        literary editing (+ edit log, + 06-factcheck.md: the edit changed no facts)
├── 07-proofread.md     proofreading (+ log)
├── 08-headlines.md     five headline options
├── 09-seo.md           optional keyword plan
├── frames/             scene candidates and the extracted illustrations
├── article.md          the final article with front matter and frames in place
└── article.habr.md     optional Habr export
```

## Pipeline

| Stage | Who | What |
|---|---|---|
| 0 | script | check `ffmpeg`, `yt-dlp`, a Whisper backend; install into a venv if missing |
| 1 | `fetch.py` | download the video (or take the local file), extract audio, normalise metadata |
| 2 | `transcribe.py --detect-only` | detect the language, then ask: output language, number of frames, SEO |
| 3 | `transcribe.py` + `frames.py scenes` | Whisper `large-v3` (faster-whisper, mlx-whisper or openai-whisper), deterministic decoding |
| 4 | `va-context-builder` | speakers, topics, glossary, recognition traps, voice |
| 5 | `chunk.py` + `va-chunk-writer` ×N + `coverage.py` | chunks processed in parallel: literal → native → terms → liveness → read-aloud; chunks that came out too short are redone |
| 6 | `va-assembler` | structure, quotes, notes, illustration points from scene changes |
| 7 | `va-fact-checker` | **gate**: nothing invented, nothing dropped, no wrong names, numbers or quotes (max 3 rounds, then the user decides) |
| 8 | `va-literary-editor` + `va-fact-checker` (diff) | living, rich literary language — not "infostyle"; then a check that editing changed no facts |
| 9 | `proofcheck.py` + `va-proofreader` | typography, spelling, punctuation, agreement, consistency |
| 10 | `va-seo-optimizer` | optional keywords (Ahrefs MCP if connected) |
| 11 | `va-headline-writer` | **gate**: five headline types, the user picks one |
| 12 | `frames.py extract` | full-size frames at the chosen timestamps, skipping black or blurred ones |
| 13 | `va-finalizer` | `article.md` with front matter, frames and the source credit |
| 14 | `habr.py` | optional Habr export |

The Russian editing and proofreading rules (`references/ru-editing.md`, `references/ru-proofreading.md`)
are adapted from a Russian book-publishing toolchain and the Lopatin spelling reference: bureaucratese,
calques, false friends, rhythm, clichés, typography (« », „ “, —, –, …, non-breaking spaces), numeral
agreement, hyphenation rules and a translation acceptance checklist. For other output languages the agents
apply the same principles in that language.

## Install

As a plugin from this repository:

```
/plugin marketplace add tym83/video-to-article
/plugin install video-to-article@video-to-article
```

Or manually: copy `skills/video-to-article` to `~/.claude/skills/` and `agents/*.md` to `~/.claude/agents/`.

System requirements: `ffmpeg`, Python 3.10+, and the Python packages `yt-dlp`, `faster-whisper` (or
`mlx-whisper` on Apple Silicon, or `openai-whisper`) and `pillow`. The skill offers to install the Python
part into `~/.venvs/video-to-article` when something is missing.

## Use

```
/video-to-article https://www.youtube.com/watch?v=…
/video-to-article ~/Movies/talk.mp4
```

The skill asks three questions after detecting the language (output language, number of illustrations,
SEO), stops at two gates (fact-check, headline) and offers a Habr export at the end.

## Habr

Habr's markdown import treats headings one level higher than usual: the article title is not a heading at
all (it goes into the separate title field) and sections start with a single `#`. `habr.py` does this
conversion, turns special blocks into plain markdown, and can insert `<cut />` after the lead.

## Scripts on their own

All scripts work without Claude:

```bash
S=skills/video-to-article/scripts
python3 $S/fetch.py "https://youtu.be/…" --workdir work
python3 $S/transcribe.py work/<id> --model large-v3-turbo
python3 $S/chunk.py work/<id>
python3 $S/frames.py work/<id> scenes
python3 $S/coverage.py work/<id> --mode translate --to ru
python3 $S/proofcheck.py article.md --lang ru --fix --report findings.md
python3 $S/habr.py article.md --cut
```

## Tests

```bash
python3 -m unittest discover -s tests
```

The suite covers the typography rules (code, links, HTML, special blocks, technical tokens like `x86-64` or
`2026-10-09` must survive), the Habr conversion, timestamps, chunking and coverage.

## License

Apache-2.0
