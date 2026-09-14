import json
import unittest
from pathlib import Path

from experiments.visibility.normalize import extract_sources
from experiments.visibility.run_shadow import FIXTURE_PATH, load_questions, render
from experiments.visibility.review_sheet import spreadsheet_safe
from experiments.visibility.compare_analysis import binary_metrics, parse_bool


class ShadowVisibilityTests(unittest.TestCase):
    def test_fixture_has_expected_distribution(self):
        payload = json.loads(Path(FIXTURE_PATH).read_text(encoding="utf-8"))
        questions = payload["questions"]
        self.assertEqual(30, len(questions))
        counts = {}
        for question in questions:
            counts[question["intent_type"]] = counts.get(question["intent_type"], 0) + 1
        self.assertEqual(
            {"discovery": 12, "branded": 6, "comparison": 6, "informational": 6},
            counts,
        )
        self.assertEqual(len(questions), len({question["id"] for question in questions}))

    def test_render_replaces_known_variables(self):
        result = render("{{city}}-{{doctor_name}}", {"city": "深圳", "doctor_name": "测试医生"})
        self.assertEqual("深圳-测试医生", result)

    def test_discovery_questions_do_not_contain_doctor_variable(self):
        payload = json.loads(Path(FIXTURE_PATH).read_text(encoding="utf-8"))
        discovery = [q for q in payload["questions"] if q["intent_type"] == "discovery"]
        self.assertTrue(discovery)
        self.assertTrue(all("{{doctor_name}}" not in q["text"] for q in discovery))

    def test_extract_sources_uses_only_http_urls(self):
        raw = {
            "web_search": [
                {"title": "A", "link": "https://example.com/a"},
                {"title": "B", "link": "javascript:alert(1)"},
            ]
        }
        sources = extract_sources(raw)
        self.assertEqual(1, len(sources))
        self.assertEqual("example.com", sources[0]["domain"])

    def test_load_questions_supports_selection(self):
        variables = {
            "doctor_name": "测试医生",
            "hospital": "测试医院",
            "department": "测试科",
            "city": "深圳",
            "specialty_primary": "方向一",
            "specialty_secondary": "方向二",
        }
        questions = load_questions(variables, ["D01", "B01"], None)
        self.assertEqual(["D01", "B01"], [question.id for question in questions])

    def test_spreadsheet_formula_is_escaped(self):
        self.assertEqual("'=SUM(A1:A2)", spreadsheet_safe("=SUM(A1:A2)"))
        self.assertEqual("普通文本", spreadsheet_safe("普通文本"))

    def test_binary_metrics(self):
        metrics = binary_metrics([(True, True), (True, False), (False, True), (False, False)])
        self.assertEqual(0.5, metrics["precision"])
        self.assertEqual(0.5, metrics["recall"])
        self.assertEqual(0.5, metrics["accuracy"])
        self.assertIs(parse_bool(""), None)


if __name__ == "__main__":
    unittest.main()
