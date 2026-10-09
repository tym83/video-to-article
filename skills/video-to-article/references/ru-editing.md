# Literary editing: living Russian

Rules for the `va-literary-editor` agent. Adapted from the style guide of a Russian book-publishing
toolchain (translation, literary editing and acceptance all judged by one rulebook, so the editor and the
reviewer never disagree about what "good" means).

Order of precedence when rules conflict: **meaning of the source > living Russian > the source's wording**.

## 0. The one test

If an edit makes a sentence "more normal" but poorer, it is not an edit. Living language is about removing
dead weight, not about flattening the speaker's voice.

## 0.5. Not "infostyle"

The goal is rich, living, literary Russian — even if it is sometimes complex. This is **not** the
"infostyle" school of editing that strips adjectives, chops every sentence to eight words and deletes every
figure of speech.

- Long, well-built sentences with participial and adverbial phrases, subordinate clauses and a period that
  breathes are welcome when they are clear. Clarity, not brevity, is the criterion.
- Keep and even enrich the vocabulary: a precise verb, a vivid image, an idiom, a turn of phrase the
  speaker used. Prefer the exact word to the common one.
- Evaluative words are fine when they carry the speaker's attitude; delete them only when they are empty
  filler or were not in the source.
- Metaphors, irony, rhetorical questions and the speaker's humour stay. If the source is witty, the article
  is witty.
- What goes is dead language (§2–5), not complexity.

## 1. Register: what to keep

- A spoken interview stays spoken: short phrases, direct address, slang and profanity if the speaker uses
  them and they fit the publication. Do not turn speech into an academic paper.
- A lecture or keynote may be elevated and rhetorical (anaphora, triads, repetition for rhythm). That is a
  property, not a defect.
- What gets fixed is deadness: bureaucratese, calques, split predicates, agentless passives, chains of
  genitives. Cleaning these up does not lower the register, it restores it.

## 2. Bureaucratese (канцелярит)

| Was | Becomes |
|---|---|
| Kubernetes **является** оркестратором | Kubernetes — оркестратор (no dash after a pronoun subject, with «не», «как», «это»: «он оркестратор», «это не оркестратор») |
| **осуществлял поставку** серверов | поставлял серверы |
| решение **было принято** | решили / команда решила |
| **в целях** ускорения | чтобы ускорить |
| **в связи с тем, что** он уехал | потому что он уехал |
| **данный** подход | этот подход |

- Split-predicate markers: *осуществлять, производить, проводить, оказывать, принимать, подвергать* +
  verbal noun. Collapse into one verb.
- Prop verbs: *являться, иметься, располагать, представлять собой*; *находиться* only when it is a prop
  («находится в стадии разработки»), not in its spatial sense («сервер находится в Амстердаме» is fine).
- Filler: *следует отметить, необходимо отметить, имеет место, в принципе, как бы, в общем-то*.
- Denominal prepositions in a bureaucratic chain: *в рамках, посредством, в качестве, по причине, в целях*.
  *Ввиду, путём, в ходе, в отношении* are normal literary words — fix them only when they pile up.

## 3. Verbal nouns

Suffixes -ание/-ение/-ация/-ность/-ство are fine on their own. Fix the pile-up: three or more in one
sentence, where the action and the actor disappear. Formula: **who — does — how**.

## 4. Calques from English

- «является тем, кто…» → a direct predicate;
- «в данной статье мы рассмотрим» → start with the substance;
- «позволяет вам», «предоставляет возможность» → a verb;
- «просто», «легко», «всего лишь» from *simply/easily/just* — remove only when empty; often it is the speaker's voice;
- «для того чтобы» → «чтобы»; «в случае, если» → «если»;
- surplus «свой»: possession is usually clear in Russian;
- time parasites from *today/nowadays*: «в наши дни», «на сегодняшний день», «в современном мире» —
  almost always delete, unless eras are really compared;
- «не просто X, а Y», «не только X, но и Y» in quantity — a hallmark of machine text; say it affirmatively;
- «то, что» repeated within one paragraph (from *the fact that*) → a noun or a direct construction in some of them;
  a single «то, что» is normal Russian;
- three near-synonyms in a row («быстро, точно и оперативно») → keep the one precise word.

## 5. False friends

| English | Not | But |
|---|---|---|
| actual | актуальный | фактический, настоящий |
| eventually | эвентуально | в итоге, со временем |
| dramatic(ally) | драматически | резко, заметно |
| consistent | консистентный | последовательный, согласованный |
| decade | декада | десятилетие |
| realize | реализовать | понять, осознать |
| sympathy | симпатия | сочувствие |
| pretend | претендовать | притворяться |
| control | контроль (always) | управление, власть над |
| original | оригинальный (always) | исходный, первоначальный |

Industry terms that Russian engineers really use (кластер, деплой, под, неймспейс, релиз, CI/CD) are not
anglicisms to purge. Purge only what a native speaker would not say: «экситинг», «майндсет», «инсайтфул».

## 6. Syntax and rhythm

- Word order follows the information flow: the known first, the new at the end.
- A third genitive in a row — break the chain with a preposition or an adjective.
- Sentences of the same length and shape read like a machine. After cleanup text often turns choppy:
  merge sentences about one thing, vary the openings, alternate long and short.
- Paragraph: 3–9 lines. A 15-line wall and a run of one-liners are equally bad.
- A long sentence is fine while its structure is clear; split it only when the reader would lose the thread
  (usually well past 40 words, or several nested clauses of the same kind).

## 7. Evaluations and clichés

- Imposed evaluation: «невероятный», «потрясающий», «уникальный», «революционный» added where the speaker
  did not say it — remove. If the speaker said it, keep it: it is their voice.
- Clichés («играет важную роль», «целый ряд», «имеет большое значение», «ни для кого не секрет»): replace with
  a precise verb or word that says what is actually meant. There are no ready-made swaps: «в полной мере» means
  «полностью», not «вполне»; a mechanical replacement changes meaning or impoverishes the sentence (§0.5).

## 8. Terminology

One term — one translation for the whole article. Synonym variety in a term is a defect: the reader
checks the wording against other sources. The canon is the glossary in `_context.md`.

## 9. Never

- **Never invent.** If an edit needs a fact absent from the transcript (a date, a name, a number), mark
  `[нужна сверка]` instead of a plausible guess. Fake precision is worse than honest uncertainty.
- **Never shorten for the sake of shortness** and never chop prose into "infostyle". Short is not the same as clear.
- **Never neutralise the register** (§1).
- **Never touch** quotations, code, commands, numbers, URLs, product names and titles.
- **Never edit silently**: every non-trivial change is logged (`before → after — reason`).

## 10. Translation acceptance checklist (when the article was translated)

1. Lost negation (*never* → an affirmation).
2. Lost condition: *only if, unless, provided that*.
3. Shifted modality: *must → может, should → должен*.
4. Changed year, number, name, version.
5. A term translated differently in different sections.
6. Translated what must not be translated (names, product names, commands).
7. Strengthening or weakening: «не поддерживается» → «поддерживается не всегда».
8. A passage of the source has no counterpart in the article and nobody flagged it.
