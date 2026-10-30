"""DefaultCleaner 单元测试。"""

import unittest

from bilibili.cleaners import DefaultCleaner


class TestDefaultCleaner(unittest.TestCase):

    def setUp(self):
        self.cleaner = DefaultCleaner()

    def test_plain_text_unchanged(self):
        self.assertEqual(self.cleaner.clean("这是一条普通评论"), "这是一条普通评论")

    def test_removes_reply_prefix(self):
        text = "回复 @某用户 : 你说的很有道理"
        self.assertEqual(self.cleaner.clean(text), "你说的很有道理")

    def test_removes_emoji_tags(self):
        text = "太棒了[大笑][滑稽]"
        self.assertEqual(self.cleaner.clean(text), "太棒了")

    def test_removes_reply_prefix_and_emoji(self):
        text = "回复 @UP主 : 支持[打call]"
        self.assertEqual(self.cleaner.clean(text), "支持")

    def test_strips_whitespace(self):
        self.assertEqual(self.cleaner.clean("  前后空格  "), "前后空格")

    def test_none_and_empty(self):
        self.assertEqual(self.cleaner.clean(None), "")
        self.assertEqual(self.cleaner.clean(""), "")

    def test_nested_brackets_single_round(self):
        # 仅去除一层 [xxx]，符合现有实现语义
        self.assertEqual(self.cleaner.clean("[a][b]"), "")


if __name__ == "__main__":
    unittest.main()
