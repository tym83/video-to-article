# video-to-article

A [Claude Code](https://claude.com/claude-code) plugin that turns a video into a finished, illustrated article.

Give it a YouTube link (or anything `yt-dlp` can download) or a local video/audio file. It transcribes the
speech with Whisper, asks whether to translate and into which language, processes the transcript chunk by
chunk so nothing is summarised away, builds a structured article, fact-checks it against the transcript,
edits it into living literary language, proofreads it, pulls frames from the video and places them in the
text, offers five headlines, and delivers the result where it will live: a Habr-ready markdown file, a draft
page on your own site styled in the site's colours and fonts (a draft pull request for git-hosted sites, a
draft post for WordPress or Ghost), or plain markdown.

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
| 14 | `blocks.py` + `habr.py` / `va-site-publisher` | delivery: Habr markdown (quotes natively or as image cards), or your own site — quotes, notes and number cards styled from the site (`sitestyle.py`), then a draft PR, a WordPress/Ghost draft or an upload bundle |

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
`mlx-whisper` on Apple Silicon, or `openai-whisper`), `pillow` and `markdown`. The skill offers to install the Python
part into `~/.venvs/video-to-article` when something is missing.

## Use

```
/video-to-article https://www.youtube.com/watch?v=…
/video-to-article ~/Movies/talk.mp4
```

The skill asks three questions after detecting the language (output language, number of illustrations,
SEO), stops at two gates (fact-check, headline) and offers a Habr export at the end.

## Where it publishes

Asked at the start, because it changes how quotes, notes and number callouts are made:

- **Habr** — no callout blocks there, so quotes become native blockquotes (searchable), or, on request,
  PNG cards (they must be uploaded and are not searchable). The title is plain text, sections start with `#`.
- **Your own site** — give its URL: `sitestyle.py` takes the colours, fonts and corner radius, `blocks.py`
  renders quotes, notes and factoids as HTML with a matching stylesheet (and cards if wanted). This needs a
  site where you can add CSS. Delivery: a git-hosted site (Hugo, Jekyll, Astro, Docusaurus, MkDocs …) gets a
  page that follows its existing posts, a local build and a **draft pull request**; WordPress and Ghost get a
  **draft post** via their API (the key stays in a file you create, never in the chat); anything else gets a
  zip bundle. Nothing is published or merged without you.
- **Plain markdown** — `article.md` with `> KIND:` blocks any layout tool can map.

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
python3 $S/sitestyle.py https://example.com -o style.json
python3 $S/blocks.py article.md html --style style.json
python3 $S/publish_cms.py bundle article.site.md --css blocks.css
```

## Tests

```bash
python3 -m unittest discover -s tests
```

The suite covers the typography rules (code, links, HTML, special blocks, technical tokens like `x86-64` or
`2026-10-09` must survive), the Habr conversion, timestamps, chunking and coverage.

## License

Apache-2.0
