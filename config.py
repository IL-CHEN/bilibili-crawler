"""
全局配置模块
============

所有可配置项均支持通过「环境变量」或「.env 文件」覆盖，优先级为：

    环境变量 > .env 文件 > 代码内默认值

使用方法：

    1. 复制项目根目录的 `.env.example` 为 `.env`；
    2. 按需修改其中的配置项。

安全提示
--------
B 站登录 Cookie（``BILI_COOKIE``）属于敏感信息，请务必通过 .env 配置，
切勿提交到公开仓库（.env 已在 .gitignore 中忽略）。
"""

import os


# ---------------------------------------------------------------------------
# 极简 .env 加载器（纯标准库实现，避免额外依赖）
# ---------------------------------------------------------------------------
def _load_dotenv(path: str) -> None:
    """
    解析 KEY=VALUE 形式的 .env 文件（支持 # 注释），
    不覆盖已存在的环境变量。
    """
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if key and key not in os.environ:
                os.environ[key] = value


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_load_dotenv(os.path.join(BASE_DIR, ".env"))


def _get(name: str, default: str) -> str:
    """读取配置项，未设置时返回默认值。"""
    return os.getenv(name, default)


# ---------------------------------------------------------------------------
# MongoDB 配置
# ---------------------------------------------------------------------------
MONGO_URI = _get("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = _get("DB_NAME", "bilibili")
COLLECTION_NAME = _get("COLLECTION_NAME", "comments")
MONGO_TIMEOUT_MS = int(_get("MONGO_TIMEOUT_MS", "3000"))

# 兼容 bilibili/main.py 的调用方式
MONGODB_CONFIG = {
    "mongo_uri": MONGO_URI,
    "db_name": DB_NAME,
}

# ---------------------------------------------------------------------------
# B 站接口请求配置
# ---------------------------------------------------------------------------
BILI_USER_AGENT = _get(
    "BILI_USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
)
BILI_COOKIE = _get("BILI_COOKIE", "")

HEADERS = {"User-Agent": BILI_USER_AGENT}
if BILI_COOKIE:
    HEADERS["Cookie"] = BILI_COOKIE

# ---------------------------------------------------------------------------
# Web 服务配置
# ---------------------------------------------------------------------------
HOST = _get("HOST", "0.0.0.0")
PORT = int(_get("PORT", "5000"))
# 生产环境请设为 0
DEBUG = _get("DEBUG", "0") == "1"
