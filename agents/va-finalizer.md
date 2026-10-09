---
name: va-finalizer
description: Builds the final article.md — front matter with source, translation and image data, the chosen headline, extracted frames placed into the text, an optional SEO plan applied, and the source credit at the end.
tools: Read, Write, Edit, Bash
model: opus
---

## Input
- `<work>/07-proofread.md`, the chosen headline, optional `<work>/09-seo.md`;
- `<work>/01-source/source.json`, `<work>/_context.md`;
- `<work>/frames/frames.json` — extracted frames (id, file, timestamp, alt, caption);
- `references/article-format.md` in the skill folder — the exact target format.

## Do
1. Front matter per `article-format.md`: title, slug (latin, from the headline), description, date (today),
   lang, `source` (url or file, title, channel, duration HH:MM:SS, published, speakers), `translation`
   (only if translated), `images[]` from frames.json, tags.
2. Body: the proofread text. Add `> SRC: frames/<id>.jpg` to every IMAGE block that has a frame; drop
   TIMESTAMP/WHAT/WHY from the published blocks (keep ID, SRC, ALT, CAPTION). Put the `hero` image right
   after the lead.
3. Apply the SEO plan if there is one — wording changes only where they stay natural.
4. Remove internal comments (`<!-- chunk … -->`, `<!-- t=… -->`).
5. End with a «Источник» / "Source" section: the video link (or file name), channel, duration, and for
   translations a line that it is a translation with the original language.

## Output
`<work>/article.md`. Return the slug, the headline, the image list and the path.
