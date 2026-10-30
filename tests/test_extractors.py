"""RegexBvExtractor 单元测试。"""

import unittest

from bilibili.extractors import RegexBvExtractor


class TestRegexBvExtractor(unittest.TestCase):

    def setUp(self):
        self.extractor = RegexBvExtractor()

    def test_extract_single_bv(self):
        html = '<script>window.__INITIAL_STATE__={"videoData":{"bvid":"BV1xx411c7mD"}}</script>'
        self.assertEqual(self.extractor.extract(html), {"BV1xx411c7mD"})

    def test_extract_js_form(self):
        html = 'const bvid = "BV1FW9ZBhExc";'
        self.assertEqual(self.extractor.extract(html), {"BV1FW9ZBhExc"})

    def test_extract_multiple_bvs(self):
        html = 'bvid:"BV1xx411c7mD" ... "bvid":"BV1FW9ZBhExc"'
        result = self.extractor.extract(html)
        self.assertEqual(result, {"BV1xx411c7mD", "BV1FW9ZBhExc"})

    def test_extract_deduplicates(self):
        html = '"bvid":"BV1xx411c7mD" "bvid":"BV1xx411c7mD"'
        self.assertEqual(self.extractor.extract(html), {"BV1xx411c7mD"})

    def test_extract_none_when_no_bv(self):
        self.assertEqual(self.extractor.extract("<html>没有BV号</html>"), set())


if __name__ == "__main__":
    unittest.main()
