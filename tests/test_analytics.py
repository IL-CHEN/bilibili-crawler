"""analytics 数据分析模块单元测试。

依赖 pandas / jieba，若未安装则自动跳过。
"""

import unittest

try:
    import analytics
    from analytics import (
        clean_text,
        compute_stats,
        get_word_freq,
        is_domestic,
        transform_region,
        query_comments,
        list_videos,
    )
    ANALYTICS_AVAILABLE = True
except ImportError as exc:  # pragma: no cover
    analytics = None
    ANALYTICS_AVAILABLE = False
    IMPORT_ERROR = exc


@unittest.skipUnless(ANALYTICS_AVAILABLE, "缺少 pandas/jieba 依赖")
class TestRegionFunctions(unittest.TestCase):

    def test_domestic_provinces(self):
        for loc in ["北京", "上海", "广东", "山东", "新疆", "香港", "澳门"]:
            self.assertTrue(is_domestic(loc), loc)

    def test_domestic_with_suffix(self):
        self.assertTrue(is_domestic("北京市"))
        self.assertTrue(is_domestic(" 上海 "))

    def test_overseas(self):
        for loc in ["海外", "日本", "美国", None, "", 123]:
            self.assertFalse(is_domestic(loc), repr(loc))

    def test_transform_region(self):
        self.assertEqual(transform_region("上海"), "上海")
        self.assertEqual(transform_region("四川成都"), "四川成都")
        self.assertEqual(transform_region("日本"), "海外")
        self.assertEqual(transform_region(None), "海外")


@unittest.skipUnless(ANALYTICS_AVAILABLE, "缺少 pandas/jieba 依赖")
class TestCleanAndWordFreq(unittest.TestCase):

    def test_clean_text_removes_urls_and_ats(self):
        text = "看看这个 https://b23.tv/abc @UP主 说的 #话题 对不对"
        cleaned = clean_text(text)
        self.assertNotIn("http", cleaned)
        self.assertNotIn("@", cleaned)
        self.assertNotIn("#", cleaned)

    def test_clean_text_keeps_chinese(self):
        self.assertEqual(clean_text("你好世界"), "你好世界")

    def test_word_freq_basic(self):
        texts = ["今天天气真不错", "今天天气很好"]
        freq = get_word_freq(texts, top_n=10)
        self.assertTrue(isinstance(freq, list))
        self.assertTrue(freq)
        # 第一个元素形如 {name, value}
        self.assertIn("name", freq[0])
        self.assertIn("value", freq[0])
        values = {item["name"]: item["value"] for item in freq}
        self.assertGreaterEqual(values.get("今天天气", 0), 2)

    def test_word_freq_empty(self):
        self.assertEqual(get_word_freq([], top_n=10), [])


class _FakeCursor:
    """模拟 pymongo 游标：支持 find/sort/skip/limit 链式调用与迭代。"""

    def __init__(self, docs, filters):
        self.docs = docs
        self.filters = filters
        self._skip = 0
        self._limit = None

    def sort(self, key):
        return self

    def skip(self, n):
        self._skip = n
        return self

    def limit(self, n):
        self._limit = n
        return self

    def __iter__(self):
        import re as _re
        matched = []
        for doc in self.docs:
            ok = True
            for key, cond in self.filters.items():
                value = doc.get(key)
                if isinstance(cond, dict) and "$regex" in cond:
                    if not _re.search(cond["$regex"], value or ""):
                        ok = False
                        break
                elif isinstance(cond, dict) and "$not" in cond:
                    if _re.search(cond["$not"]["$regex"], value or ""):
                        ok = False
                        break
                elif value != cond:
                    ok = False
                    break
            if ok:
                matched.append(dict(doc))
        start = self._skip
        end = None if self._limit is None else start + self._limit
        return iter(matched[start:end])


class _FakeCollection:
    """内存版评论集合，用于验证查询逻辑。"""

    def __init__(self, docs):
        self.docs = list(docs)

    def count_documents(self, filters):
        return len(list(_FakeCursor(self.docs, filters)))

    def find(self, filters, projection=None):
        return _FakeCursor(self.docs, filters)

    def aggregate(self, pipeline):
        # 仅支持本项目使用的 $group + $sort + $limit 简化实现
        from collections import defaultdict

        # 解析 $group 的 _id 表达式，如 {"_id": "$bv"}
        group_field = None
        limit = None
        for stage in pipeline:
            if isinstance(stage, dict) and "$group" in stage:
                expr = stage["$group"].get("_id")
                if isinstance(expr, str) and expr.startswith("$"):
                    group_field = expr[1:]
            if isinstance(stage, dict) and "$limit" in stage:
                limit = stage["$limit"]
        assert group_field, "测试用聚合仅支持按字段分组"

        grouped = defaultdict(list)
        for doc in self.docs:
            grouped[doc.get(group_field)].append(doc)
        rows = []
        for key, items in grouped.items():
            row = {"_id": key, "count": len(items)}
            c_times = [i.get("latest_c_time") for i in items]
            crawls = [i.get("latest_crawl_at") for i in items]
            row["latest_c_time"] = max((x for x in c_times if x is not None), default=None)
            row["latest_crawl_at"] = max((x for x in crawls if x is not None), default=None)
            rows.append(row)
        rows.sort(key=lambda r: r["count"], reverse=True)
        return rows[:limit] if limit else rows


@unittest.skipUnless(ANALYTICS_AVAILABLE, "缺少 pandas/jieba 依赖")
class TestQueryFunctions(unittest.TestCase):

    def setUp(self):
        self.docs = [
            {"bv": "BV1AA", "rp_id": "1", "user_name": "小明", "content": "好好看啊", "ip": "上海", "c_time": 1700000000},
            {"bv": "BV1AA", "rp_id": "2", "user_name": "小红", "content": "支持 UP", "ip": "北京", "c_time": 1700000100},
            {"bv": "BV2BB", "rp_id": "3", "user_name": "Tom", "content": "great video", "ip": "日本", "c_time": 1700000200},
        ]

    def test_query_by_keyword(self):
        result = query_comments(_FakeCollection(self.docs), keyword="支持")
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["items"][0]["user_name"], "小红")

    def test_query_by_region_domestic(self):
        result = query_comments(_FakeCollection(self.docs), region="国内")
        self.assertEqual(result["total"], 2)

    def test_query_by_region_overseas(self):
        result = query_comments(_FakeCollection(self.docs), region="海外")
        self.assertEqual(result["total"], 1)

    def test_query_by_region_specific(self):
        result = query_comments(_FakeCollection(self.docs), region="上海")
        self.assertEqual(result["total"], 1)

    def test_query_pagination(self):
        result = query_comments(_FakeCollection(self.docs), page=2, page_size=2)
        self.assertEqual(result["total"], 3)
        self.assertEqual(result["page"], 2)
        self.assertEqual(len(result["items"]), 1)

    def test_list_videos(self):
        videos = list_videos(_FakeCollection(self.docs), limit=10)
        self.assertEqual(videos[0]["bv"], "BV1AA")
        self.assertEqual(videos[0]["count"], 2)


@unittest.skipUnless(ANALYTICS_AVAILABLE, "缺少 pandas/jieba 依赖")
class TestComputeStats(unittest.TestCase):

    def test_stats_basic(self):
        docs = [
            {"bv": "BV1AA", "user_id": "1", "user_name": "小明", "content": "好看", "ip": "上海", "c_time": 1700000000},
            {"bv": "BV1AA", "user_id": "2", "user_name": "小红", "content": "真棒", "ip": "北京", "c_time": 1700000100},
            {"bv": "BV2BB", "user_id": "3", "user_name": "Tom", "content": "great", "ip": "日本", "c_time": 1700000200},
        ]
        stats = compute_stats(_FakeCollection(docs), top_n=20)
        self.assertEqual(stats["total"], 3)
        self.assertEqual(stats["domestic_total"], 2)
        self.assertEqual(stats["overseas_total"], 1)
        self.assertEqual(stats["total_videos"], 2)
        self.assertEqual(stats["total_users"], 3)

    def test_stats_empty(self):
        stats = compute_stats(_FakeCollection([]))
        self.assertEqual(stats["total"], 0)
        self.assertEqual(stats["time_dist"], [])


if __name__ == "__main__":
    unittest.main()
