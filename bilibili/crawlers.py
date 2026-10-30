import random
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Set
from urllib.parse import quote

from bilibili.cleaners import DefaultCleaner
from bilibili.extractors import RegexBvExtractor
from bilibili.fetchers import HtmlFetcher, ApiFetcher
from bilibili.interfaces import Fetcher, Extractor, CommentParser, Cleaner, Repository
from bilibili.parsers import BilibiliCommentParser
from bilibili.repositories import FileRepository, MongoRepository


# BV 爬虫骨架
class BvCrawler(ABC):
    """BV 号爬虫模板方法"""
    def __init__(self, keyword: str):
        self.keyword = keyword.strip()
        self.fetcher = HtmlFetcher()
        self.extractor = self._create_extractor()
        self.repository = self._create_repository()

    @abstractmethod
    def _create_extractor(self) -> Extractor:
        pass

    @abstractmethod
    def _create_repository(self) -> Repository:
        pass

    @abstractmethod
    def _build_url(self, page: int) -> str:
        pass

    @abstractmethod
    def _get_params(self, page: int) -> dict:
        pass

    def crawl(self, start_page: int, end_page: int) -> List[str]:
        all_bvs: Set[str] = set()
        for page in range(start_page, end_page + 1):
            url = self._build_url(page)
            params = self._get_params(page)
            try:
                html = self.fetcher.fetch(url, params)
                bvs = self.extractor.extract(html)
                if not bvs:
                    print("未提取到 BV，可能触发反爬，终止翻页")
                    break
                all_bvs |= bvs
            except Exception as e:
                print(f"第 {page} 页请求失败: {e}")
                break
        bv_list = list(all_bvs)
        if bv_list:
            self.repository.save_bvs(bv_list)
        return bv_list


# 评论爬虫骨架
class CommentCrawler(ABC):
    """评论爬虫模板方法"""
    def __init__(self, bv_list: List[str]):
        self.bv_list = bv_list
        self.fetcher = self._create_fetcher()
        self.parser = self._create_parser()
        self.cleaner = self._create_cleaner()
        self.repository = self._create_repository()

    @abstractmethod
    def _create_fetcher(self) -> Fetcher:
        pass

    @abstractmethod
    def _create_parser(self) -> CommentParser:
        pass

    @abstractmethod
    def _create_cleaner(self) -> Cleaner:
        pass

    @abstractmethod
    def _create_repository(self) -> Repository:
        pass

    @abstractmethod
    def _build_main_url(self, bv: str) -> str:
        pass

    @abstractmethod
    def _build_main_params(self, bv: str, page: int) -> dict:
        pass

    @abstractmethod
    def _build_sub_url(self, bv: str, rpid: str) -> str:
        pass

    @abstractmethod
    def _build_sub_params(self, bv: str, rpid: str, page: int) -> dict:
        pass

    def _random_sleep(self, min_sec=1, max_sec=2):
        time.sleep(random.uniform(min_sec, max_sec))

    def crawl(self):
        for bv in self.bv_list:
            print(f"\n开始爬取视频 {bv} 的评论...")
            video_comments = []
            page = 0
            # 主评论分页
            while True:
                self._random_sleep()
                page += 1
                try:
                    url = self._build_main_url(bv)
                    params = self._build_main_params(bv, page)
                    resp = self.fetcher.fetch(url, params)
                    main_comments, need_sub_rpids = self.parser.parse_main(resp)
                    if not main_comments:
                        break
                    for c in main_comments:
                        c['bv'] = bv
                    video_comments.extend(main_comments)

                    # 子评论分页
                    for rpid in need_sub_rpids:
                        sub_page = 0
                        while True:
                            self._random_sleep()
                            sub_page += 1
                            sub_url = self._build_sub_url(bv, rpid)
                            sub_params = self._build_sub_params(bv, rpid, sub_page)
                            sub_resp = self.fetcher.fetch(sub_url, sub_params)
                            sub_comments = self.parser.parse_sub(sub_resp)
                            if not sub_comments:
                                break
                            for c in sub_comments:
                                c['bv'] = bv
                            video_comments.extend(sub_comments)
                except Exception as e:
                    print(f"爬取视频 {bv} 主评论第{page}页出错: {e}")
                    break

            # 清洗 + 打上入库时间戳
            crawl_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for c in video_comments:
                c['content'] = self.cleaner.clean(c['content'])
                c['crawl_at'] = crawl_at

            # 存储
            self.repository.save_comments(video_comments)
            print(f"视频 {bv} 评论爬取完成，共 {len(video_comments)} 条")

        print("\n所有 BV 评论爬取完毕")


# 具体爬虫实现
class BilibiliBvCrawler(BvCrawler):
    """B 站关键词搜索 BV 爬虫"""
    def _create_extractor(self) -> Extractor:
        return RegexBvExtractor()

    def _create_repository(self) -> Repository:
        return FileRepository("bilibili_bv.txt", "comments")

    def _build_url(self, page: int) -> str:
        return f"https://search.bilibili.com/all?keyword={quote(self.keyword)}"

    def _get_params(self, page: int) -> dict:
        return {
            'page': str(page),
            'o': str(42 * (page - 1))
        }


class BilibiliCommentCrawler(CommentCrawler):
    """B 站评论爬虫，存入 MongoDB"""
    def __init__(self, bv_list: List[str], mongo_uri="mongodb://localhost:27017", db_name="bilibili"):
        self.mongo_uri = mongo_uri
        self.db_name = db_name
        super().__init__(bv_list)

    def _create_fetcher(self) -> Fetcher:
        return ApiFetcher()

    def _create_parser(self) -> CommentParser:
        return BilibiliCommentParser()

    def _create_cleaner(self) -> Cleaner:
        return DefaultCleaner()

    def _create_repository(self) -> Repository:
        return MongoRepository(self.mongo_uri, self.db_name)

    def _build_main_url(self, bv: str) -> str:
        return 'https://api.bilibili.com/x/v2/reply/main'

    def _build_main_params(self, bv: str, page: int) -> dict:
        return {
            'next': page,
            'type': 1,
            'oid': bv,
            'mode': 3
        }

    def _build_sub_url(self, bv: str, rpid: str) -> str:
        return 'https://api.bilibili.com/x/v2/reply/reply'

    def _build_sub_params(self, bv: str, rpid: str, page: int) -> dict:
        return {
            'oid': bv,
            'type': 1,
            'ps': 20,
            'root': rpid,
            'pn': page
        }
