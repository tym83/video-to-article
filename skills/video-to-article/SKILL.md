---
name: video-to-article
description: Turn a video (YouTube or any yt-dlp link, or a local video/audio file) into a finished, illustrated article — Whisper transcription, optional translation into any language, faithful chunk-by-chunk processing, structure, fact-check gate, literary editing into living language, professional proofreading, extracted frames placed in the text, headline options, optional SEO, and a Habr-ready export. Use when the user gives a video link or file and wants an article, post, longread or transcript-based text from it.
argument-hint: <video URL or path to a video/audio file>
---

# /video-to-article — video → article

You orchestrate the whole pipeline. Mechanical stages run as scripts from `scripts/` in this skill's folder
(`${CLAUDE_SKILL_DIR}`, the directory of this SKILL.md). Language and editorial stages are
**delegated to subagents** with the Agent tool: `video-to-article:va-*` in a plugin install, `va-*` in a manual
install. Subagents do not know where this skill lives: **always pass absolute paths** — the work folder and every
file under `${CLAUDE_SKILL_DIR}` an agent needs (`references/*.md`, `scripts/proofcheck.py`). Keep every intermediate artefact in the work folder; never keep the article "in your head".

Talk to the user in their language. Report briefly after each stage: what is done, where the artefact is,
what comes next or which gate is waiting.

Input: `$ARGUMENTS` — a URL or a file path. If empty, ask for it.

## Stage 0 — environment
Check `ffmpeg -version`, `yt-dlp --version` (only for URLs) and a Whisper backend
(`python3 -c "import faster_whisper"`, or `mlx_whisper` on Apple Silicon, or `whisper`). If something is
missing, install into a dedicated venv and use its python for all scripts:
```bash
python3 -m venv ~/.venvs/video-to-article            # or: uv venv ~/.venvs/video-to-article
~/.venvs/video-to-article/bin/pip install -U yt-dlp faster-whisper pillow markdown
# Apple Silicon (much faster): ~/.venvs/video-to-article/bin/pip install -U mlx-whisper
```
ffmpeg itself comes from the system package manager (`brew install ffmpeg`, `apt install ffmpeg`).
Tell the user what you installed.

## Stage 1 — fetch
```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/fetch.py "<URL or path>" --workdir ./video-to-article
```
The last line is the work folder `<work>`. All paths below are inside it.

## Stage 2 — language and the questions
```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/transcribe.py <work> --detect-only --model small
```
Then ask in **one** AskUserQuestion call:
1. **Output language** — "keep <detected language> (clean-up and literary editing only)" /
   "translate into Russian" / "translate into English" (+ Other for any language). Recommend keeping the
   original when it already matches the user's language.
2. **Illustrations** — "auto (about one per 600–800 words)" / "3–5" / "8–12" / "no frames".
3. **SEO pass** — "no" / "yes (Ahrefs if connected)".
4. **Where will it be published** — "Habr" / "my own site (custom layout)" / "plain markdown".

If the answer is **own site**, ask in plain text for the site URL and how it is managed (a git repository —
give its URL; WordPress; Ghost; something else), and say up front that styled quotes, notes and number cards
work only on a site where CSS can be added. Then take the site's look and show it for confirmation:
```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/sitestyle.py <site-url> -o <work>/style.json
```
(background, text, accent colours, fonts, corner radius; the user may correct any of them). For WordPress or
Ghost, ask the user to save the key into a file themselves with a `!` command — see
`${CLAUDE_SKILL_DIR}/references/publishing.md` — and never ask them to paste it into the chat.

If `source.json` shows an audio-only input (no video stream), skip question 2: there are no frames.
Keep the answers: they go into the `## Job` section of `_context.md` (Stage 4) and every agent reads them there.

## Stage 3 — transcription
```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/transcribe.py <work> --model large-v3 --language <detected>
```
`large-v3` on CPU takes roughly the video's duration or longer; for videos over an hour, or when the user is
in a hurry, use `--model large-v3-turbo`. Warn the user about the expected time before starting.
Then, in parallel with the next stage, detect scenes for illustrations (skip if "no frames"):
```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/frames.py <work> scenes
```

## Stage 4 — context
Delegate **va-context-builder** with `<work>` and the job, with ISO 639-1 codes: mode (`translate en→ru` or
`clean ru`), source and output language, number of illustrations, SEO yes/no, input kind. Wait for
`_context.md`. If it lists speaker names or facts to verify that you cannot settle, ask the user.

## Stage 5 — chunks, processed in parallel
```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/chunk.py <work>
```
For **every** chunk in `03-chunks/` launch **va-chunk-writer** (several Agent calls in one message), passing
the chunk path, the previous chunk's path (context only), `<work>/_context.md` and
`${CLAUDE_SKILL_DIR}/references/ru-editing.md`. Each writes `04-text/NN.md`. Re-run missing or failed chunks, then check
that nothing was summarised away:
```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/coverage.py <work> --mode <clean|translate> --to <output language code>
```
Re-run every chunk that `coverage.md` flags as too short.

## Stage 6 — assembly
Delegate **va-assembler**: `<work>`, the number of illustrations, `${CLAUDE_SKILL_DIR}/references/article-format.md`
and `${CLAUDE_SKILL_DIR}/references/publishing.md` (placement rules for quotes, notes and factoids).
Output `05-assembled.md`.

## Stage 7 — fact-check (GATE)
Delegate **va-fact-checker** in audit mode → `05-factcheck.md`. On **FAIL** fix the listed places yourself with
Edit (never re-run the assembler on the whole text) and re-check. At most three rounds; if BLOCKERs remain, show
them to the user and ask how to proceed. Never continue silently with a BLOCKER.

## Stage 8 — literary editing
Run the style hints, then delegate **va-literary-editor** with `${CLAUDE_SKILL_DIR}/references/ru-editing.md`:
```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/proofcheck.py <work>/05-assembled.md --lang <lang> --report <work>/05-proofcheck.md
```
Output `06-edited.md` + `06-edit-log.md`. The target is rich, living literary language — not "infostyle".
Then delegate **va-fact-checker** in diff mode (`06-edited.md` against `05-assembled.md`) → `06-factcheck.md`
and fix any BLOCKER: editing must not change facts, numbers, modality or drop content.

## Stage 9 — proofreading
Delegate **va-proofreader** with `${CLAUDE_SKILL_DIR}/references/ru-proofreading.md` and `${CLAUDE_SKILL_DIR}/scripts/proofcheck.py`.
Output `07-proofread.md` + `07-proofread-log.md`.

## Stage 10 — SEO (optional)
If the user wanted it, delegate **va-seo-optimizer** → `09-seo.md`.

## Stage 11 — headline (GATE, user)
Delegate **va-headline-writer** (with `09-seo.md` if it exists) → `08-headlines.md`. Show the five options and ask the user to pick one (or
approve the recommended one, or write their own).

## Stage 12 — frames
Skip when the job has 0 illustrations or the input is audio-only.
```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/frames.py <work> extract --from <work>/07-proofread.md
```
Look at a few of the extracted frames with Read; if one is clearly bad (closed eyes, motion blur, a black
screen), change its TIMESTAMP in `07-proofread.md` and re-run extraction.

## Stage 13 — final article
Delegate **va-finalizer** with the chosen headline and `${CLAUDE_SKILL_DIR}/references/article-format.md` → `<work>/article.md` (front matter,
frames placed, source credit). If it returns leftover `[VERIFY]` / `[UNVERIFIED]` / `**[?]:**` markers, resolve them
with the user before calling it done. Show the user
the path, the headline, the word count and the list of images.

## Stage 14 — delivery
**Own site.** Render the special blocks in the site's style, then delegate **va-site-publisher** with the site
URL, the route, `style.json`, `blocks.css`, `article.site.md`, the paths of `publish_cms.py` and
`publishing.md`:
```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/blocks.py <work>/article.md html --style <work>/style.json
python3 ${CLAUDE_SKILL_DIR}/scripts/blocks.py <work>/article.md cards --style <work>/style.json   # if the user wants cards too
```
For a git-hosted site it returns a pushed branch and a prepared draft-PR text: show the text to the user and
run `gh pr create --draft` only after they approve. WordPress/Ghost: a draft post URL. Otherwise: a zip bundle.

**Habr.** Ask how quotes, notes and factoids should look: "native Habr quotes (recommended: searchable)" or
"image cards" (warn: the cards must be uploaded to Habr, their text is not searchable). Then:
```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/habr.py <work>/article.md --cut
# with cards (style from the user's site if they gave one, otherwise neutral):
python3 ${CLAUDE_SKILL_DIR}/scripts/blocks.py <work>/article.md cards [--style <work>/style.json]
python3 ${CLAUDE_SKILL_DIR}/scripts/habr.py <work>/article.md --cut --cards <work>/cards
```
On Habr the title is plain text on the first line (it goes into the title field) and sections start with a
single `#`. Remind the user that frames must be uploaded to Habr (or pass `--images-base <url>` once they
are hosted somewhere) and that translated articles are marked as translations with the original link.
Details: `${CLAUDE_SKILL_DIR}/references/habr.md`.

## Orchestrator rules
- Structured artefacts between stages; re-read files instead of relying on memory.
- Language work is delegated to `va-*` agents — context hygiene and quality.
- Names, numbers and quotes are verified, never guessed; doubtful places are marked `[VERIFY]`
  and reported, not smoothed over.
- No public actions (publishing, uploading, posting, opening PRs) without the user's explicit go-ahead;
  everything that reaches a site is a draft or a draft PR. Credentials live in files the user created, never
  in the chat, the work folder or a repository.
