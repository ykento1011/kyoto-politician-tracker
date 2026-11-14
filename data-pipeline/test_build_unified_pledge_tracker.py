"""Offline regression tests: never import or execute the tracker generator."""
import ast
from pathlib import Path
import unittest
from unittest.mock import call, patch


SOURCE = Path(__file__).with_name("build_unified_pledge_tracker.py")
FRONTEND = Path("fixture") / "frontend" / "public" / "data"
DATA = Path("fixture") / "data-pipeline" / "data"
CASES = {
    "kyoto": (
        ["pledge_tracker_kyoto.json", "kyoto_pledge_tracker.json", "pledge_tracker.json"],
        ["kyoto_statements_summary.json", "kyoto_statements.json", "statements_summary.json", "statements.json"],
    ),
    "osaka": (
        ["pledge_tracker_osaka.json", "osaka_pledge_tracker.json", "osaka/pledge_tracker.json"],
        ["osaka_statements_summary.json", "osaka_statements.json"],
    ),
    "nagoya": (
        ["pledge_tracker_nagoya.json", "nagoya_pledge_tracker.json"],
        ["nagoya_statements_summary.json", "nagoya_statements.json"],
    ),
    "yokohama": (
        ["pledge_tracker_yokohama.json", "yokohama_pledge_tracker.json"],
        ["yokohama_statements_summary.json", "yokohama_statements.json"],
    ),
    "kobe": (
        ["pledge_tracker_kobe.json", "kobe_pledge_tracker.json"],
        ["kobe_statements_summary.json", "kobe_statements.json"],
    ),
}


class SyntaxTests(unittest.TestCase):
    def test_entire_module_parses(self):
        ast.parse(SOURCE.read_text(encoding="utf-8-sig"), filename=str(SOURCE))


class GetPathsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8-sig"), filename=str(SOURCE))
        function = next(
            node for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "get_paths"
        )
        # Only define this function; discard all imports, dotenv setup and main.
        isolated = ast.Module(body=[function], type_ignores=[])
        namespace = {
            "__builtins__": {"next": next},
            "FRONTEND_DATA": FRONTEND,
            "DATA_DIR": DATA,
        }
        exec(compile(isolated, str(SOURCE), "exec"), namespace)
        cls.get_paths = staticmethod(namespace["get_paths"])

    def test_output_names_counts_and_uniqueness_for_five_cities(self):
        with patch.object(Path, "exists", return_value=False):
            for city, (outputs, _) in CASES.items():
                with self.subTest(city=city):
                    actual = self.get_paths(city)["out_files"]
                    self.assertEqual(actual, [FRONTEND / name for name in outputs])
                    self.assertEqual(len(actual), 3 if city in ("kyoto", "osaka") else 2)
                    self.assertEqual(len(actual), len(set(actual)))

    def test_other_input_paths_and_kyoto_aliases(self):
        with patch.object(Path, "exists", return_value=False):
            for city in CASES:
                with self.subTest(city=city):
                    paths = self.get_paths(city)
                    paths.pop("out_files")
                    self.assertEqual(paths, {
                        "pledges": DATA / f"{city}_councilor_pledges.json",
                        "pledges_alt": DATA / "councilor_pledges.json" if city == "kyoto" else None,
                        "pledges_fallback": FRONTEND / f"pledge_tracker_{city}_2.json",
                        "statements": None,
                        "votes": FRONTEND / f"{city}_votes_summary.json",
                        "votes_alt": FRONTEND / "votes_summary.json" if city == "kyoto" else None,
                        "issues": FRONTEND / f"{city}_bill_issues.json",
                        "issues_alt": FRONTEND / "bill_issues.json" if city == "kyoto" else None,
                        "stmt_embeddings": DATA / f"embeddings_{city}_statements.json",
                        "pledge_embeddings": DATA / f"embeddings_{city}_pledges.json",
                        "bill_embeddings": DATA / f"embeddings_{city}_bills.json",
                    })

    def test_statement_candidates_in_priority_order(self):
        for city, (_, names) in CASES.items():
            candidates = [FRONTEND / name for name in names]
            for index, expected in enumerate(candidates):
                with self.subTest(city=city, first_available=names[index]):
                    available = set(candidates[index:])
                    with patch.object(Path, "exists", autospec=True, side_effect=available.__contains__) as exists:
                        self.assertEqual(self.get_paths(city)["statements"], expected)
                    self.assertEqual(exists.call_args_list, [call(p) for p in candidates[:index + 1]])

    def test_missing_statement_candidates_return_none(self):
        for city, (_, names) in CASES.items():
            with self.subTest(city=city):
                with patch.object(Path, "exists", autospec=True, return_value=False) as exists:
                    self.assertIsNone(self.get_paths(city)["statements"])
                self.assertEqual(exists.call_args_list, [call(FRONTEND / name) for name in names])

    def test_other_cities_do_not_use_kyoto_legacy_statements(self):
        available = {FRONTEND / "statements_summary.json", FRONTEND / "statements.json"}
        with patch.object(Path, "exists", autospec=True, side_effect=available.__contains__):
            self.assertEqual(self.get_paths("kyoto")["statements"], FRONTEND / "statements_summary.json")
            for city in ("osaka", "nagoya", "yokohama", "kobe"):
                with self.subTest(city=city):
                    self.assertIsNone(self.get_paths(city)["statements"])


if __name__ == "__main__":
    unittest.main()
