"""Regression tests for the pipeline scripts. Run: python3 -m unittest discover -s tests"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "skills" / "video-to-article" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import coverage  # noqa: E402
import frames  # noqa: E402
import proofcheck as pc  # noqa: E402
import transcribe  # noqa: E402

NB = " "


def fix(text):
    return pc.apply_fixes(text, "ru")


class Typography(unittest.TestCase):
    def test_special_block_does_not_stop_typography(self):
        out = fix('Лид.\n\n> IMAGE:\n> ID: hero\n> ALT: "схема"\n\nВторой абзац - тут "два"...\n')
        self.assertIn("абзац" + NB + "— тут «два»…", out)
        self.assertIn("> ALT: «схема»", out)
        self.assertIn("> ID: hero", out)

    def test_horizontal_rules_in_body_are_not_front_matter(self):
        out = fix('Текст\n\n---\n\nтут "кавычки"\n\n---\n')
        self.assertIn("«кавычки»", out)

    def test_front_matter_untouched(self):
        src = '---\ntitle: "A - B"\n---\nТекст - вот\n'
        out = fix(src)
        self.assertTrue(out.startswith('---\ntitle: "A - B"\n---\n'))

    def test_quotes_next_to_code_and_links(self):
        out = fix('Команда "`kubectl apply`" и "[доку](https://x.io/a-b)" тут\n')
        self.assertIn("«`kubectl apply`»", out)
        self.assertIn("«[доку](https://x.io/a-b)»", out)

    def test_nested_quotes_with_existing_guillemets(self):
        self.assertIn("«Проект „Альфа“»", fix('«Проект "Альфа"»\n'))

    def test_quote_after_colon_opens(self):
        self.assertIn("сказал:«да»", fix('Он сказал:"да"\n'))

    def test_inches_are_not_quotes(self):
        self.assertIn('27"', fix('Монитор 27" стоит\n'))

    def test_technical_tokens_are_not_ranges(self):
        for tok in ("1.2-3", "2026-10-09", "x86-64", "H100-80GB", "8-800-555-35-35", "10:00-12:00"):
            self.assertIn(tok, fix(f"Значение {tok} здесь\n"), tok)

    def test_real_range(self):
        self.assertIn("2014–2015", fix("В 2014-2015 годах\n"))

    def test_subtraction_is_not_a_dash(self):
        self.assertIn("5 - 3", fix("Считаем 5 - 3\n"))

    def test_negative_number_gets_minus(self):
        self.assertIn("−5", fix("Было -5 градусов\n"))

    def test_dot_names_survive(self):
        out = fix("Файл .env и платформа .NET, а также Node.js .\n")
        self.assertIn("Файл .env", out)
        self.assertIn("платформа .NET", out)
        self.assertIn("Node.js.", out)

    def test_html_and_indented_code_untouched(self):
        src = 'Текст\n\n<img src="a.jpg" alt="Схема">\n\n    echo "hi" - x\n'
        out = fix(src)
        self.assertIn('<img src="a.jpg" alt="Схема">', out)
        self.assertIn('    echo "hi" - x', out)

    def test_question_dots_kept(self):
        self.assertIn("Правда?..", fix("Правда?..\n"))

    def test_percent_and_initials(self):
        out = fix("Рост 30% и 40 %. Пушкин А. С. писал, А. Пушкин тоже.\n")
        self.assertIn("30" + NB + "%", out)
        self.assertIn("40" + NB + "%", out)
        self.assertIn("Пушкин" + NB + "А." + NB + "С.", out)
        self.assertIn("А." + NB + "Пушкин", out)

    def test_other_language_fix_refused(self):
        with self.assertRaises(SystemExit):
            pc.apply_fixes("Bonjour : oui !", "fr")


class StyleHints(unittest.TestCase):
    def groups(self, text):
        return [g for _, g, _, _ in pc.style_report(text, "ru")]

    def test_no_false_positives(self):
        self.assertEqual([], self.groups("Данные лежат в базе. Повышение производительности приложения. Проводить исследование. "
                                         "Важно то, что он пришёл.\n"))

    def test_real_bureaucratese(self):
        g = self.groups("Данный подход является основой и осуществляет поставку решений в рамках проекта.\n")
        self.assertGreaterEqual(g.count("канцелярит"), 3)

    def test_repeated_to_chto(self):
        self.assertIn("калька", self.groups("Важно то, что он сказал, и то, что он сделал.\n"))

    def test_mixed_alphabets(self):
        self.assertIn("орфография", self.groups("Работаем с Kubеrnetes\n"))


class Habr(unittest.TestCase):
    def run_habr(self, text):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "a.md"
            p.write_text(text, encoding="utf-8")
            subprocess.run([sys.executable, str(SCRIPTS / "habr.py"), str(p)], check=True, capture_output=True)
            return (Path(d) / "a.habr.md").read_text(encoding="utf-8")

    def test_title_and_heading_levels(self):
        out = self.run_habr('---\ntitle: "Заголовок"\n---\nЛид.\n\n## Раздел\n\n### Подраздел\n')
        self.assertTrue(out.startswith("Заголовок\n"))
        self.assertIn("\n# Раздел\n", out)
        self.assertIn("\n## Подраздел\n", out)
        self.assertNotIn("# Заголовок", out)

    def test_code_blocks_untouched(self):
        out = self.run_habr("# Title\n\nЛид.\n\n```bash\n# install deps\n## not a heading\n```\n\n## Раздел\n")
        self.assertIn("# install deps\n## not a heading", out)
        self.assertTrue(out.startswith("Title\n"))

    def test_adjacent_blocks_and_wrapped_fields(self):
        out = self.run_habr("Лид.\n\n> IMAGE:\n> ID: img-01\n> SRC: frames/img-01.jpg\n> ALT: кадр\n"
                            "> PULLQUOTE:\n> TEXT: «Под — это стручок!»\n> ATTRIBUTION: Андрей\n\n"
                            "> FACTOID:\n> NUMBER: 7\n> TEXT: спиц у штурвала\n> и продолжение текста\n")
        self.assertIn("![кадр](frames/img-01.jpg)", out)
        self.assertIn("> «Под — это стручок!»", out)
        self.assertIn("спиц у штурвала и продолжение текста", out)


class Small(unittest.TestCase):
    def test_srt_time_rounding(self):
        self.assertEqual("00:01:00,000", transcribe.srt_time(59.9996))
        self.assertEqual("01:02:03,450", transcribe.srt_time(3723.45))

    def test_timestamp_forms(self):
        self.assertEqual(754, frames.sec("[00:12:34]"))
        self.assertAlmostEqual(83.5, frames.sec("00:01:23,5"))
        self.assertEqual(754, frames.sec("12:34"))
        with self.assertRaises(ValueError):
            frames.sec("about a minute")

    def test_image_requests_stop_at_next_block(self):
        reqs = frames.parse_requests("> IMAGE:\n> ID: a\n> TIMESTAMP: 00:00:05\n> IMAGE:\n> ID: b\n> TIMESTAMP: 00:00:09\n")
        self.assertEqual(["a", "b"], [r["id"] for r in reqs])

    def test_coverage_text_cleanup(self):
        self.assertEqual("hello world", coverage.source_text("[00:00:01] hello\n[00:00:02] world\n"))
        self.assertEqual("Привет мир", coverage.plain("<!-- t=1 -->\n**Аня:** Привет\n\n> IMAGE:\n> ID: x\n\nмир"))

    def test_empty_transcript_exits_cleanly(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "02-transcript").mkdir()
            (Path(d) / "02-transcript" / "transcript.json").write_text(json.dumps({"segments": []}))
            r = subprocess.run([sys.executable, str(SCRIPTS / "chunk.py"), d], capture_output=True, text=True)
            self.assertNotEqual(0, r.returncode)
            self.assertIn("empty", r.stderr)
            self.assertNotIn("Traceback", r.stderr)


if __name__ == "__main__":
    unittest.main()
