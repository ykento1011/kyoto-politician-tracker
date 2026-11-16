import unittest

from research_topic import parse_keywords


class ParseKeywordsTest(unittest.TestCase):
    def test_mixed_separators_preserve_first_occurrence(self):
        self.assertEqual(parse_keywords("予算、 教育,,予算"), ["予算", "教育"])
