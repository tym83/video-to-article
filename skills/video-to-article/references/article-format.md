# Article format

The pipeline keeps one markdown dialect from assembly to the final file. Special blocks are blockquotes
whose first line is a marker `> KIND:`; every block ends with a blank line. Field names stay in English and
upper case; field values are in the article language.

## Special blocks

```markdown
> FACTOID:
> NUMBER: 12
> TEXT: years in production — and still no full-cluster outage

> PULLQUOTE:
> TEXT: «Pod — это стручок!»
> ATTRIBUTION: Speaker Name

> NOTE: What is etcd
> TEXT: a short reference note for readers who do not know the term

> IMAGE:
> ID: img-03
> TIMESTAMP: 00:24:11
> WHAT: the speaker draws the control loop on a whiteboard
> WHY: illustrates the paragraph about reconciliation
> ALT: the speaker drawing a reconciliation loop on a whiteboard
> CAPTION: The whole idea of Kubernetes fits on one whiteboard.
```

- `IMAGE` blocks carry `TIMESTAMP` until frames are extracted; after `frames.py extract` the finalizer adds
  `> SRC: frames/<id>.jpg`.
- `hero` is a reserved image ID: the opening frame of the article.
- Interview lines: `**Name:** text`, names from `_context.md`.

## Final file (`article.md`)

```markdown
---
title: "Chosen headline"
slug: chosen-headline
description: "150–160 characters, with the primary keyword when SEO was run"
date: 2026-10-09
lang: ru
source:
  type: interview        # interview | talk | lecture | podcast | panel | tutorial | video
  url: "https://www.youtube.com/watch?v=…"   # or the local file name
  title: "Original video title"
  channel: "…"
  duration: "01:12:40"
  published: 2026-09-30
  speakers:
    - name: "…"
      role: "…"
translation:
  from: en
  to: ru                 # omit the block when the article was not translated
images:
  - id: hero
    file: frames/hero.jpg
    timestamp: "00:00:42"
    alt: "…"
tags: [ … ]
---

Lead paragraph (2–4 sentences: who, what, why it matters).

> IMAGE:
> ID: hero
> SRC: frames/hero.jpg
> ALT: …

## First strong section heading

…

## Source

Video: [Original title](url) · Channel · Duration.
```

Rules:
- No H1 in the body: the title lives in the front matter.
- 5–12 H2 sections per hour of video; H3 only to split a long section. Headings are strong and specific,
  not descriptive («Почему мы выключили половину кластера — и никто не заметил», not «Об отказоустойчивости»).
- The video is always credited: link in the front matter and a visible «Источник»/«Source» section at the end.
- A site that needs its own layout (shortcodes, Hugo, a CMS) gets a separate adapter step; the core
  pipeline stays site-agnostic.
