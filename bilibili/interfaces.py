from abc import ABC, abstractmethod
from typing import List, Dict, Set, Any


class Fetcher(ABC):
    """数据获取接口"""

    @abstractmethod
    def fetch(self, url: str, params: dict | None = None) -> Any:
        pass


class Extractor(ABC):
    """数据提取接口"""

    @abstractmethod
    def extract(self, html: str) -> Set[str]:
        pass


class CommentParser(ABC):
    """评论报文解析器接口"""

    @abstractmethod
    def parse_main(self, response: dict) -> tuple:
        """
        :return: (评论列表, 含有子评论的主评论 rpid 列表)
        评论列表元素为 dict，如：{rp_id, user_id, user_name, content, ip}
        """
        pass

    @abstractmethod
    def parse_sub(self, response: dict) -> List[Dict]:
        """返回子评论列表"""
        pass


class Cleaner(ABC):
    """数据清洗接口"""

    @abstractmethod
    def clean(self, text: str) -> str:
        pass


class Repository(ABC):
    """数据持久化接口"""

    @abstractmethod
    def save_bvs(self, bvs: List[str]) -> None:
        pass

    @abstractmethod
    def save_comments(self, comments: List[Dict]) -> None:
        pass
