"""
B 站评论爬虫命令行入口
======================

流程：搜索关键词 -> 提取 BV 号 -> 爬取评论 -> 入库 MongoDB。

用法示例：
    # 爬取关键词「Python 教程」前 5 页搜索结果的视频评论
    python -m bilibili.main --keyword "Python 教程" --start 1 --end 5

    # 只爬取 1 页
    python -m bilibili.main --keyword "美食" --start 1 --end 1
"""

import argparse

from bilibili.crawlers import BilibiliBvCrawler, BilibiliCommentCrawler
from config import MONGODB_CONFIG


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="B 站评论爬虫：关键词 → BV 号 → 评论入库 MongoDB"
    )
    parser.add_argument(
        "--keyword", required=True,
        help="搜索关键词，如：Python 教程",
    )
    parser.add_argument(
        "--start", type=int, default=1,
        help="搜索起始页（默认 1）",
    )
    parser.add_argument(
        "--end", type=int, default=10,
        help="搜索结束页（默认 10）",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.start < 1 or args.end < args.start:
        raise SystemExit("错误：起始页必须 >= 1，且结束页必须 >= 起始页")

    # 1. 根据关键词爬取 BV 号
    print(f"== 开始搜索关键词「{args.keyword}」第 {args.start}-{args.end} 页 ==")
    bv_crawler = BilibiliBvCrawler(args.keyword)
    bv_list = bv_crawler.crawl(args.start, args.end)
    print(f"共获取 {len(bv_list)} 个 BV 号")

    if not bv_list:
        print("未获取到 BV 号，程序退出")
        return

    # 2. 用 BV 列表爬取评论，存入 MongoDB
    comment_crawler = BilibiliCommentCrawler(
        bv_list,
        **MONGODB_CONFIG,
    )
    comment_crawler.crawl()


if __name__ == "__main__":
    main()
