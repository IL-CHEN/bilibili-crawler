"""
B 站评论数据看板 —— Flask 应用入口
====================================

启动方式：
    python app.py

环境依赖：
    MongoDB 服务（默认 localhost:27017），连接配置见 config.py / .env

接口一览：
    GET /                 看板页面
    GET /api/health       MongoDB 健康检查
    GET /api/stats        全局统计数据（地域/占比/排行/词云/趋势）
    GET /api/comments     评论分页查询（支持 bv/keyword/user/region 过滤）
    GET /api/bvs          视频评论数排行
"""

import logging

from flask import Flask, jsonify, render_template, request
from pymongo import MongoClient
from pymongo.errors import PyMongoError

from analytics import compute_stats, list_videos, query_comments
from config import (
    COLLECTION_NAME,
    DB_NAME,
    DEBUG,
    HOST,
    MONGO_TIMEOUT_MS,
    MONGO_URI,
    PORT,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# MongoDB 连接（懒连接：构造时不立即建连，首个操作才连接）
# ---------------------------------------------------------------------------
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=MONGO_TIMEOUT_MS)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

app = Flask(__name__)


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
def _api_error(message: str, status: int = 500):
    """统一的 API 错误响应。"""
    return jsonify({"ok": False, "error": message}), status


def _handle_api_error(func, *args, **kwargs):
    """把异常统一转成 JSON 错误响应。"""
    try:
        return func(*args, **kwargs)
    except PyMongoError as exc:
        logger.error("MongoDB 操作失败: %s", exc)
        return _api_error(f"数据库连接失败：{exc}", 503)
    except Exception as exc:  # 兜底，避免把堆栈抛给前端
        logger.exception("API 处理异常")
        return _api_error(str(exc), 500)


# ---------------------------------------------------------------------------
# 页面路由
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


# ---------------------------------------------------------------------------
# API 路由
# ---------------------------------------------------------------------------
@app.route("/api/health")
def health():
    """MongoDB 健康检查。"""
    try:
        db.command("ping")
        return jsonify({"ok": True, "mongo": "connected", "db": DB_NAME})
    except PyMongoError as exc:
        logger.warning("MongoDB 健康检查失败: %s", exc)
        return jsonify(
            {"ok": False, "mongo": "disconnected", "db": DB_NAME, "error": str(exc)}
        ), 503


@app.route("/api/stats")
def stats():
    """全局统计数据。"""
    def _do():
        return jsonify({"ok": True, "data": compute_stats(collection)})
    return _handle_api_error(_do)


@app.route("/api/comments")
def comments():
    """评论分页查询。"""
    def _do():
        page = request.args.get("page", 1, type=int) or 1
        page_size = request.args.get("page_size", 20, type=int) or 20
        page = max(page, 1)
        page_size = min(max(page_size, 1), 100)
        result = query_comments(
            collection,
            bv=request.args.get("bv", "").strip() or None,
            keyword=request.args.get("keyword", "").strip() or None,
            user=request.args.get("user", "").strip() or None,
            region=request.args.get("region", "").strip() or None,
            sort=request.args.get("sort", "time"),
            page=page,
            page_size=page_size,
        )
        return jsonify({"ok": True, "data": result})
    return _handle_api_error(_do)


@app.route("/api/bvs")
def bvs():
    """视频评论数排行（供筛选下拉框使用）。"""
    def _do():
        return jsonify({"ok": True, "data": list_videos(collection, limit=100)})
    return _handle_api_error(_do)


if __name__ == "__main__":
    logger.info("B 站评论看板启动: http://%s:%s", HOST, PORT)
    app.run(debug=DEBUG, host=HOST, port=PORT)
