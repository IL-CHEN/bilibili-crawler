from bilibili.interfaces import Fetcher
from bilibili.session import SessionManager


class HtmlFetcher(Fetcher):
    """获取 HTML 文本"""

    def __init__(self):
        self.session = SessionManager().get_session()

    def fetch(self, url: str, params: dict = None) -> str:
        print(f"正在请求 HTML: {url}")
        resp = self.session.get(url, params=params)
        resp.raise_for_status()
        return resp.text


class ApiFetcher(Fetcher):
    """获取 JSON 数据"""

    def __init__(self):
        self.session = SessionManager().get_session()

    def fetch(self, url: str, params: dict = None) -> dict:
        print(f"正在请求 API: {url} params={params}")
        resp = self.session.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        if data.get('code') != 0:
            raise Exception(f"API 返回错误: {data.get('message')}")
        return data
