#!/usr/bin/env python3
"""Mechanical proofreading pass for Russian (basic typography for English).

Usage:
    proofcheck.py <article.md> [--lang ru] [--fix] [--report out.md]

Two layers:
  * typography (safe, --fix applies it, ru and en only): «ёлочки» and „лапки“ instead of straight quotes,
    em dash between words, en dash in numeric ranges, a minus sign for negative numbers, … for three dots,
    non-breaking spaces after one-letter prepositions/conjunctions, in initials, before units and %, after
    № and §, after a dialogue dash, in «т. е.», «т. д.» etc.; no space before punctuation.
  * style hints (report only, never auto-fixed): bureaucratese, English calques, false friends, clichés,
    imposed evaluations, mixed Latin/Cyrillic letters in a word, doubled words, unbalanced pairs, very long
    sentences. They are hints for the editor, not orders: complexity is not a defect.

Never touched: front matter, fenced and indented code, inline code, HTML comments and tags, link targets,
URLs, and the structural fields of special blocks (ID, TIMESTAMP, SRC, FILE, NUMBER, HREF). The text fields
of special blocks (TEXT, ALT, CAPTION, …) are proofread like any other text.
"""
import argparse
import re
import sys
from pathlib import Path

NBSP = " "
MASK_OPEN, MASK_CLOSE = "", ""

PROTECT = re.compile(
    r"\A---\n(?s:.*?)\n---\n"                     # front matter (only at the very top)
    r"|^```(?s:.*?)^```[^\n]*$"                   # fenced code
    r"|^(?: {4}|\t)[^\n]*$"                       # indented code lines
    r"|`[^`\n]+`"                                 # inline code
    r"|<!--(?s:.*?)-->"                           # html comments
    r"|<[A-Za-z/!][^>\n]*>"                       # html tags
    r"|\]\([^)\n]*\)"                             # link targets
    r"|https?://[^\s)>\]]+"                       # bare urls
    r"|^> (?:ID|TIMESTAMP|SRC|FILE|NUMBER|HREF):[^\n]*$"  # structural special-block fields
    r"|^> [A-Z_]+:",                              # the marker part of any special-block line
    re.M)


def mask(text):
    saved = []

    def keep(m):
        saved.append(m.group(0))
        return f"{MASK_OPEN}{len(saved) - 1}{MASK_CLOSE}"
    return PROTECT.sub(keep, text), saved


def unmask(text, saved):
    return re.sub(f"{MASK_OPEN}(\\d+){MASK_CLOSE}", lambda m: saved[int(m.group(1))], text)


# ---------------------------------------------------------------- typography
OPENERS = set(" \t\n([{—–-«„/:…" + NBSP)


def fix_quotes(s):
    """Pair straight quotes per paragraph, aware of quotes that are already typographic."""
    out, depth = [], 0
    for i, ch in enumerate(s):
        if ch == "\n" and i + 1 < len(s) and s[i + 1] == "\n":
            depth = 0
        if ch == "«":
            depth += 1
        elif ch == "»":
            depth = max(0, depth - 1)
        if ch != '"':
            out.append(ch)
            continue
        prev = s[i - 1] if i else "\n"
        if prev.isdigit() and depth == 0:          # 27" — inches, not a quote
            out.append(ch)
            continue
        if prev in OPENERS or i == 0:
            out.append("«" if depth == 0 else "„")
            depth += 1
        else:
            depth = max(0, depth - 1)
            out.append("»" if depth == 0 else "“")
    return "".join(out)


NUM_L = r"(?<![\w.,:/\-–−])"
NUM_R = r"(?![\w.,:/\-–−])"


def typo_ru(s):
    s = fix_quotes(s)
    s = re.sub(r"(?<![?!.])\.\.\.(?!\.)", "…", s)
    s = re.sub(NUM_L + r"(\d+)[-–—](\d+)" + NUM_R, r"\1–\2", s)                 # 2014–2015 (no spaces)
    s = re.sub(r"(?<=[\s(])-(?=\d)", "−", s)                                      # negative numbers
    s = re.sub(r"(?<=[^\s\d]) [-–] (?=\S)|(?<=\S) [-–] (?=[^\s\d])", f"{NBSP}— ", s)  # dash, but not 5 - 3
    s = re.sub(r"(?<=\S) — ", f"{NBSP}— ", s)
    s = re.sub(r"(?m)^— ", f"—{NBSP}", s)                                         # dialogue line
    s = re.sub(r"[ \t]+([,;!?…»)])", r"\1", s)                                    # no space before punctuation
    s = re.sub(r"[ \t]+([.:])(?=\s|$)", r"\1", s)                                 # … but keep «Файл .env»
    s = re.sub(r"([«„(])[ \t]+", r"\1", s)
    s = re.sub(r"(?<=\S)[ \t]{2,}(?=\S)", " ", s)
    s = re.sub(rf"(?<![\w{NBSP}\-])([аАвВиИкКоОсСуУяЯ]) (?=\S)", rf"\1{NBSP}", s)  # one-letter words
    s = re.sub(r"\b([А-ЯЁ]\.) ?([А-ЯЁ]\.) ([А-ЯЁ][а-яё]+)", rf"\1{NBSP}\2{NBSP}\3", s)   # А. С. Пушкин
    s = re.sub(r"\b([А-ЯЁ][а-яё]+) ([А-ЯЁ]\.) ?([А-ЯЁ]\.)", rf"\1{NBSP}\2{NBSP}\3", s)   # Пушкин А. С.
    s = re.sub(r"\b([А-ЯЁ]\.) ([А-ЯЁ][а-яё]{2,})", rf"\1{NBSP}\2", s)                   # А. Пушкин
    s = re.sub(r"(№|§) ?(?=\d)", rf"\1{NBSP}", s)
    s = re.sub(r"(\d) ?%", rf"\1{NBSP}%", s)
    s = re.sub(r"(\d) (₽|руб\.|тыс\.|млн|млрд|км|км/ч|м|кг|г\.|гг\.|ч|мин|ГБ|МБ|ТБ|Гбит/с|ГГц|°C)(?=[\s.,;:!?)]|$)",
               rf"\1{NBSP}\2", s)
    for a, b in (("т", "е"), ("т", "к"), ("т", "н"), ("т", "п"), ("т", "д"), ("н", "э")):
        s = re.sub(rf"\b{a}\.\s?{b}\.", f"{a}.{NBSP}{b}.", s)
    return s


def typo_en(s):
    s = re.sub(r"(?<![?!.])\.\.\.(?!\.)", "…", s)
    s = re.sub(r"(?<=[^\s\d]) - (?=\S)|(?<=\S) - (?=[^\s\d])", " — ", s)
    s = re.sub(NUM_L + r"(\d+)-(\d+)" + NUM_R, r"\1–\2", s)
    s = re.sub(r"[ \t]+([,;!?…)])", r"\1", s)
    s = re.sub(r"[ \t]+([.:])(?=\s|$)", r"\1", s)
    return s


def apply_fixes(text, lang):
    if lang not in ("ru", "en"):
        raise SystemExit(f"--fix supports ru and en only; for '{lang}' apply that language's typography by hand")
    masked, saved = mask(text)
    fixed = (typo_ru if lang == "ru" else typo_en)(masked)
    return unmask(fixed, saved)


# ---------------------------------------------------------------- style hints (report only)
W = r"(?<![А-Яа-яЁё])"
E = r"(?![А-Яа-яЁё])"
SP = r"[  ]"


def ph(words):
    """A phrase pattern whose spaces also match non-breaking spaces."""
    return words.replace(" ", SP)


STYLE_RU = [
    ("канцелярит", "связка «является» — тире или смысловой глагол",
     W + r"явля(?:ет|ют)ся(?:" + SP + r"+[а-яё]+){0,3}" + SP + r"+[а-яё]{3,}(?:ом|ём|ем|ой|ёй|ей|ью|ами|ями|ыми|ими)" + E),
    ("канцелярит", "отымённый предлог в канцелярской цепочке",
     W + ph(r"(?:в целях|с целью|в связи с|по причине|при наличии|в рамках|на предмет|в плане|посредством|в качестве)") + E),
    ("канцелярит", "«данный/указанный» вместо «этот»",
     W + r"(?:данн(?:ый|ого|ому|ым|ом|ая|ой|ую|ое)|вышеуказанн\w+|вышеупомянут\w+|нижеследующ\w+)" + E),
    ("канцелярит", "расщеплённое сказуемое — свернуть в один глагол (осуществлять поставку → поставлять)",
     W + r"(?:осуществля\w+|осуществи\w+|оказыва\w+|оказа\w+|подверга\w+)" + SP + r"+(?:[а-яё]+" + SP
     + r"+)?[а-яё]{4,}(?:ание|ения|ение|ению|анию|ацию|ации|ация)" + E),
    ("канцелярит", "подпорка без смысла",
     W + ph(r"(?:следует отметить|необходимо отметить|стоит отметить|хотелось бы отметить|имеет место"
            r"|не представляется возможным|носит характер)") + E),
    ("калька", "«является тем, кто…» — сказать глаголом", W + r"явля(?:ет|ют)ся" + SP + r"+(?:тем|той|теми)," + SP + r"+(?:кто|что|который)"),
    ("калька", "«не просто X, а Y» — почерк машинного текста", W + ph("не просто") + r"\b[^.!?]{1,60}," + SP + r"?а" + SP),
    ("калька", "паразит времени из «today/nowadays»",
     W + ph(r"(?:в наши дни|на сегодняшний день|в современном мире|всё большую актуальность)") + E),
    ("калька", "«позволяет вам / предоставляет возможность» → глагол", W + ph(r"(?:позволяет вам|предоставляет возможность)") + E),
    ("ложный друг", "actual ≠ актуальный, eventually ≠ эвентуально, dramatic ≠ драматически, consistent ≠ консистентный",
     W + r"(?:эвентуально|драматически|консистентн\w+|декад[аеуы])" + E),
    ("штамп", "штамп — заменить точным словом по смыслу (готовых пар нет)",
     W + ph(r"(?:играет (?:важную|ключевую) роль|целый ряд|имеет большое значение|ни для кого не секрет)") + E),
    ("оценка", "усилитель — проверить, говорил ли так спикер",
     W + r"(?:невероятн\w+|потрясающ\w+|колоссальн\w+|грандиозн\w+)" + E),
]
MIXED = re.compile(r"\b(?=\w*[A-Za-z])(?=\w*[А-Яа-яЁё])\w+\b")
DOUBLE = re.compile(r"\b(\w{2,})\s+\1\b", re.I)
TO_CHTO = re.compile(W + ph("то, что") + E)


def style_report(text, lang):
    masked, _ = mask(text)
    findings = []
    for n, line in enumerate(masked.split("\n"), 1):
        plain = re.sub(f"{MASK_OPEN}\\d+{MASK_CLOSE}", " ", line)
        if not plain.strip():
            continue
        if lang == "ru":
            for group, msg, pat in STYLE_RU:
                for m in re.finditer(pat, plain, re.I):
                    findings.append((n, group, msg, m.group(0)))
            k = len(TO_CHTO.findall(plain))
            if k >= 2:
                findings.append((n, "калька", "«то, что» несколько раз в абзаце — часть заменить", f"то, что ×{k}"))
            if '"' in plain:
                findings.append((n, "типографика", "прямые кавычки вместо «ёлочек»", plain.strip()[:60]))
        for m in MIXED.finditer(plain):
            if not re.fullmatch(r"[A-Za-z0-9_]+|[А-Яа-яЁё0-9_]+", m.group(0)):
                findings.append((n, "орфография", "латиница и кириллица в одном слове (артефакт распознавания)", m.group(0)))
        for m in DOUBLE.finditer(plain):
            findings.append((n, "повтор", "слово повторено подряд (если не намеренно)", m.group(0)))
        if plain.count("«") != plain.count("»") or plain.count("(") != plain.count(")"):
            findings.append((n, "парные знаки", "непарные кавычки или скобки в абзаце", plain.strip()[:60]))
        for sent in re.split(r"(?<=[.!?…])\s+", plain):
            if len(sent.split()) > 45:
                findings.append((n, "ритм", "предложение длиннее 45 слов — проверить, не теряется ли нить (сложность не дефект)",
                                 sent.strip()[:80] + "…"))
    return findings


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("article")
    ap.add_argument("--lang", default="ru")
    ap.add_argument("--fix", action="store_true", help="apply the safe typography layer in place (ru, en)")
    ap.add_argument("--report", help="write findings as markdown here")
    a = ap.parse_args()
    path = Path(a.article)
    text = path.read_text(encoding="utf-8")
    if a.fix:
        fixed = apply_fixes(text, a.lang)
        changed = sum(1 for x, y in zip(text, fixed) if x != y) + abs(len(text) - len(fixed))
        path.write_text(fixed, encoding="utf-8")
        text = fixed
        print(f"typography: {changed} characters changed")
    found = style_report(text, a.lang)
    rep = ["# Proofcheck findings", "", f"File: `{path}` · {len(found)} findings · hints, not orders", "",
           "| line | group | issue | fragment |", "|---|---|---|---|"]
    rep += [f"| {n} | {g} | {m} | {frag.replace('|', '/')} |" for n, g, m, frag in found]
    if a.report:
        Path(a.report).write_text("\n".join(rep) + "\n", encoding="utf-8")
    groups = {}
    for _, g, _, _ in found:
        groups[g] = groups.get(g, 0) + 1
    print("findings: " + (", ".join(f"{g} {c}" for g, c in sorted(groups.items())) or "none"))


if __name__ == "__main__":
    sys.exit(main())
