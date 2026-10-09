# Publishing targets

Asked at the start (Stage 2), because the target changes how special blocks are made.

| Target | Special blocks (FACTOID / PULLQUOTE / NOTE) | Delivery |
|---|---|---|
| **Habr** | Habr has no callout blocks. Default: native blockquotes (searchable, copyable). Option: PNG cards from `blocks.py cards` — warn that cards must be uploaded to Habr and their text is not searchable. | `habr.py` → `article.habr.md`, the user pastes it into Habr's markdown import |
| **Own site, custom layout** | Styled from the site: `sitestyle.py <url>` → `style.json` (show the palette and fonts to the user for confirmation) → `blocks.py html` (semantic HTML + `blocks.css`) and optionally `blocks.py cards`. Warn: this only works where you can add CSS and raw HTML is allowed (Hugo: `markup.goldmark.renderer.unsafe: true`). | `va-site-publisher`: git repo → draft PR; WordPress/Ghost → draft post; otherwise a zip bundle |
| **Plain markdown** | Kept as `> KIND:` blocks (any layout tool or human can map them) | `article.md` |

## Placement rules for special blocks (all targets)

- Never directly next to an image: at least one paragraph of text between a block and an IMAGE.
- Never two special blocks in a row.
- At most one block of each kind per section; FACTOID only for a real, striking number from the video.
- Not in the lead and not right after a heading — a block comments on text, so text comes first.

## Credentials

- **git-hosted sites**: the user's own `gh` / git access; nothing is stored by the pipeline.
- **WordPress**: an Application Password; **Ghost**: an Admin API key. Ask the user to put it in a file
  themselves, without pasting it into the chat, e.g.
  `! read -s -p "token: " T && printf %s "$T" > ~/.config/video-to-article/<site>.key && chmod 600 ~/.config/video-to-article/<site>.key`
  and pass only the file path to the scripts.
- Everything is created as a **draft** / **draft PR**. Publishing, merging and pushing to the default branch
  are the user's actions.
