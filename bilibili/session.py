import requests

from config import HEADERS


class SessionManager:
    """
    单例模式：全局唯一的请求会话，复用 TCP 连接并统一设置 headers
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.session = requests.Session()
            cls._instance.session.headers.update(HEADERS)
        return cls._instance

    def get_session(self) -> requests.Session:
        return self.session
