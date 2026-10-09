# Proofreading: Russian code of practice

Rules for the `va-proofreader` agent. Adapted from a Russian book-publishing proofreading manual and the
spelling reference by V. V. Lopatin («Правила русской орфографии и пунктуации»). The mechanical part is
run by `scripts/proofcheck.py`; the rest needs a human-grade read.

## 1. Typography (proofcheck.py --fix does this; verify the result)

- Quotes: «ёлочки» outside, „лапки“ inside. No straight quotes in Russian text.
- Dash: em dash (—) between words, with a non-breaking space before and a normal space after; at the start of
  a dialogue line «— Реплика» with a non-breaking space after the dash. A hyphen (-) never stands for a dash.
- Ranges in words: a dash with spaces («май — июнь»); approximate counts in words: a hyphen («два-три дня»).
- Minus sign (−) for negative numbers, not a hyphen: −5 °C, от −5 до −10.
- «?..» and «!..» stay as they are (not «?…»).
- Ordinal suffixes: «5-й», «в 1990-х», «20-летие» — never «5-ый».
- Numeric ranges: en dash without spaces: 2014–2015, 10–15 мин.
- Ellipsis: one character (…). At the start of a sentence it is not separated from the next word.
- Punctuation (. , ; : ! ? …) is never separated from the preceding word.
- Non-breaking spaces: after one-letter prepositions and conjunctions (в, к, с, у, о, а, и, я); in initials
  (А. С. Пушкин); between a number and its unit (5 ГБ, 30 %, 2 млн); after № and §; in «т. е.», «т. д.».
- Ё (rules of 2006, §10): selective by default — where without it a word is misread (всё/все, узнаём/узнаем),
  in rare words and in proper names. Consistent ё everywhere is allowed as an editorial decision; then it must be
  consistent, never mixed. Beware of false ё — these are written with е: афера, опека, гренадер, бытие, житие, оседлый.
- Paired signs: every opening bracket or quote has its closing pair.

## 2. Spelling and grammar

- Agreement of numerals with nouns: «21 сервер», «22 сервера», «25 серверов».
- Gender of borrowed words is fixed by the glossary (e.g. «кластер» м. р., «нода» ж. р.).
- Hyphenated vs. joined vs. separate (Lopatin §151–153):
  - a prefix or first part before a proper name gets a hyphen: анти-Маяковский, пол-Москвы;
  - «пол» before a noun that has its own modifier is written separately: пол чайной ложки, пол Московской области;
  - пол- before a vowel, «л» or a capital letter is hyphenated (пол-арбуза, пол-лимона, пол-Европы,
    пол-одиннадцатого), otherwise joined (полчаса); полу- is always joined (полуостров, полукруг).
- Capitalisation of products and organisations follows their own spelling (Kubernetes, GitHub, CNCF).
- No mixed Latin/Cyrillic letters inside a word (a frequent speech-recognition artefact: «Kubеrnetes»
  with a Cyrillic «е»). proofcheck.py flags them.

## 3. Punctuation

- Introductory words are set off by commas (конечно, кстати, по-моему), but «однако» at the start of a
  clause meaning «но» is not.
- Compound conjunctions take one comma, before the whole conjunction («потому что», «несмотря на то что»,
  «так как»); it may split only for emphasis («потому, что…»). Set phrases take no comma: «делай что хочешь»,
  «не то что», «во что бы то ни стало», «как ни в чём не бывало».
- Comma before «что», «чтобы», «который», «если» in a complex sentence; no comma inside fixed phrases
  («как правило» is introductory, «как раз» is not).
- Direct speech and dialogue: «— Реплика, — сказал он. — Продолжение.» In interviews use the
  `**Имя:** текст` format consistently instead of dialogue dashes.
- No comma between the subject and the predicate, even when the subject is long.

## 4. Consistency across the article

- Abbreviations, units, dates, numbers, names, headings and captions are formatted the same everywhere.
- A term is spelled one way everywhere (glossary in `_context.md`).
- Numbers (Milchin): single-digit numbers without units are written in words; in a row with multi-digit
  numbers everything is digits («от 5 до 15»); approximate numbers in words («около тридцати»); a sentence never
  starts with a digit. Units, versions, money, percentages — digits. Four-digit numbers are not split (1500);
  from five digits the groups are separated with a non-breaking thin space (12 500).
- Percent: «30 %» with a non-breaking space — one format throughout the article.
- Dates: «12 октября 2026 года», not «12.10.2026», in running text.
- Abbreviations with spaces: «т. е.», «т. к.», «т. н.», «и т. п.», «и т. д.», «до н. э.».

## 5. Facts and source

- Check unfamiliar words, numbers, dates and names against the transcript and `_context.md`.
- If the transcript itself looks wrong, do not "correct" it blindly — flag `[нужна сверка]` for the editor.

## 6. Do not touch

Code, commands, configuration, URLs, product names, quotations in the original language, and special-block
field names (`> IMAGE:`, `> TIMESTAMP:` …).

## 7. Final pass checklist

- [ ] proofcheck.py run with --fix, report reviewed, every finding fixed or consciously kept
- [ ] no straight quotes, no hyphen-as-dash, no double spaces
- [ ] ё where required
- [ ] numerals agree with nouns
- [ ] headings: no full stop at the end, consistent capitalisation
- [ ] captions and alt texts proofread too
- [ ] every `[нужна сверка]` resolved or reported to the user
