# Habr formatting

Habr's markdown import treats heading levels one step higher than standard markdown:

| In `article.md` | On Habr |
|---|---|
| title in front matter / `# Title` | **plain text**, first line — paste it into the separate title field |
| `## Section` | `# Section` |
| `### Subsection` | `## Subsection` |
| `#### Minor` | `### Minor` |

`scripts/habr.py` does the conversion and also:
- drops the front matter and HTML comments;
- turns FACTOID / PULLQUOTE / NOTE into blockquotes and IMAGE into `![alt](src)` plus an italic caption;
- with `--images-base URL` rewrites frame paths to an uploaded location (Habr does not take local files:
  upload the frames to habrastorage first, or drag them into the editor and replace the links);
- with `--cut` inserts `<cut />` after the lead paragraph (the feed preview ends there);
- with `--cards DIR` replaces FACTOID / PULLQUOTE / NOTE by PNG cards made by `blocks.py … cards`. Habr has no
  callout blocks, so the default is native blockquotes; cards look richer but must be uploaded and their
  text is not searchable — tell the user before choosing them.

Before publishing on Habr also check:
- tags and hubs are chosen in the editor, not in markdown;
- code blocks have a language for highlighting;
- the source video is credited at the end (Habr moderators expect it for translations: mark the post as
  a translation and give the original link when the article is translated).
