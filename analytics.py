"""
数据分析模块
============

基于 MongoDB 中的评论数据计算看板所需的各种统计指标，
与 Flask 视图层解耦，便于单元测试与复用。

数据字段说明（评论文档）
------------------------
+---------------+----------------------------------------+
| 字段          | 说明                                   |
+---------------+----------------------------------------+
| rp_id         | 评论 ID                                |
| user_id       | 用户 ID                                |
| user_name     | 用户昵称                               |
| content       | 评论文本                               |
| ip            | 评论 IP 归属地（如：上海 / 海外）      |
| bv            | 视频 BV 号                             |
| video_url     | 视频链接                               |
| c_time        | 评论发布时间（Unix 秒，新爬数据才有）  |
| crawl_at      | 抓取入库时间（新爬数据才有）           |
+---------------+----------------------------------------+
"""

import os
import re
from collections import Counter
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import jieba
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# 国内地点判定（基于 ip 字段）
# ---------------------------------------------------------------------------
CHINA_LOCATIONS = {
    "北京", "上海", "天津", "重庆",
    "河北", "山西", "辽宁", "吉林", "黑龙江", "江苏", "浙江", "安徽",
    "福建", "江西", "山东", "河南", "湖北", "湖南", "广东", "海南",
    "四川", "贵州", "云南", "陕西", "甘肃", "青海", "台湾", "内蒙古",
    "广西", "西藏", "宁夏", "新疆", "香港", "澳门",
    "广州", "深圳", "成都", "杭州", "武汉", "西安", "南京", "苏州", "郑州",
    "长沙", "东莞", "佛山", "宁波", "青岛", "厦门", "大连", "南昌", "合肥",
}

# 按名称长度降序生成 "^(北京|上海|...)" 正则，用于 MongoDB 区域过滤
_DOMESTIC_REGEX = "^(?:" + "|".join(
    sorted(CHINA_LOCATIONS, key=len, reverse=True)
) + ")"


def is_domestic(location_str) -> bool:
    """判断 IP 归属地是否为国内。"""
    if not location_str or not isinstance(location_str, str):
        return False
    location_str = location_str.strip()
    if location_str in CHINA_LOCATIONS:
        return True
    for loc in CHINA_LOCATIONS:
        if location_str.startswith(loc):
            return True
    return False


def transform_region(location_str) -> str:
    """把 IP 归属地规整为「具体地区」或「海外」。"""
    return location_str if is_domestic(location_str) else "海外"


def domestic_filter(domestic: bool) -> dict:
    """
    构造 MongoDB 区域过滤条件。
    domestic=True  -> ip 以任一国内地区名开头
    domestic=False -> ip 不以任何国内地区名开头（含 ip 缺失，视为海外）
    """
    if domestic:
        return {"ip": {"$regex": _DOMESTIC_REGEX}}
    return {"ip": {"$not": {"$regex": _DOMESTIC_REGEX}}}


# ---------------------------------------------------------------------------
# 停用词
# ---------------------------------------------------------------------------
def _load_stopwords() -> set:
    """加载百度停用词表。"""
    path = os.path.join(BASE_DIR, "baidu_stopwords.txt")
    with open(path, "r", encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}


STOPWORDS = _load_stopwords()


# ---------------------------------------------------------------------------
# 文本分词与词频统计
# ---------------------------------------------------------------------------
def clean_text(text) -> str:
    """清洗评论文本：去除链接、@提及、话题标签及特殊符号。"""
    if not isinstance(text, str):
        return ""
    text = re.sub(r"http\S+|www\S+|@\S+|#\S+", "", text)
    text = re.sub(r"[^\u4e00-\u9fa5a-zA-Z0-9]", "", text)
    return text


def get_word_freq(texts, top_n: int = 80) -> List[Dict]:
    """
    统计词频，返回形如 [{name: 词, value: 次数}, ...] 的列表，
    供 ECharts 词云图使用。
    """
    words = []
    for text in texts:
        cleaned = clean_text(text)
        if not cleaned:
            continue
        for word in jieba.lcut(cleaned):
            if len(word) >= 2 and word not in STOPWORDS:
                words.append(word)
    counter = Counter(words)
    return [{"name": w, "value": cnt} for w, cnt in counter.most_common(top_n)]


# ---------------------------------------------------------------------------
# 时间处理
# ---------------------------------------------------------------------------
def _to_date(value) -> Optional[str]:
    """
    把评论时间统一转成 YYYY-MM-DD。
    兼容两种格式：
      - c_time：Unix 秒（int/float）
      - crawl_at：字符串时间（YYYY-MM-DD HH:MM:SS）
    无法解析时返回 None。
    """
    if value is None:
        return None
    if isinstance(value, (int, float)) and value > 0:
        return datetime.fromtimestamp(value).strftime("%Y-%m-%d")
    if isinstance(value, str) and value.strip():
        try:
            return datetime.strptime(value[:10], "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            return None
    return None


def _build_time_dist(dates: pd.Series, days: int = 30) -> List[Dict]:
    """
    根据日期序列生成最近 days 天（含今天）的每日评论数序列，
    缺失的日期补 0，返回 [{date, count}, ...]。
    """
    end = datetime.now().date()
    start = end - timedelta(days=days - 1)
    date_counts = Counter(d for d in dates if d)
    result = []
    cursor = start
    while cursor <= end:
        key = cursor.strftime("%Y-%m-%d")
        result.append({"date": key, "count": date_counts.get(key, 0)})
        cursor += timedelta(days=1)
    return result


# ---------------------------------------------------------------------------
# 统计查询
# ---------------------------------------------------------------------------
def compute_stats(collection, top_n: int = 80) -> Dict:
    """
    计算看板所需的全部统计指标。
    空库时返回全零结构。
    """
    cursor = collection.find(
        {}, {"ip": 1, "user_id": 1, "user_name": 1, "bv": 1,
             "content": 1, "c_time": 1, "crawl_at": 1}
    )
    df = pd.DataFrame(list(cursor))
    total = len(df)

    empty = {
        "total": 0,
        "domestic_total": 0,
        "overseas_total": 0,
        "total_videos": 0,
        "total_users": 0,
        "region_dist": [],
        "top_users": [],
        "top_videos": [],
        "time_dist": [],
        "wordcloud_data": [],
        "latest_crawl_at": None,
    }
    if total == 0:
        return empty

    # 地域处理
    df["region"] = df["ip"].apply(transform_region)
    domestic_df = df[df["region"] != "海外"]
    region_counts = domestic_df["region"].value_counts().reset_index()
    region_counts.columns = ["name", "value"]
    region_dist = region_counts.to_dict(orient="records")

    overseas_total = int((df["region"] == "海外").sum())
    domestic_total = total - overseas_total

    # 用户 / 视频排行
    user_counts = df["user_name"].value_counts().head(10).reset_index()
    user_counts.columns = ["name", "count"]
    top_users = user_counts.to_dict(orient="records")

    video_counts = df["bv"].value_counts().head(10).reset_index()
    video_counts.columns = ["name", "count"]
    top_videos = video_counts.to_dict(orient="records")

    # 时间趋势（优先 c_time，其次 crawl_at）
    dates = df["c_time"].apply(_to_date) if "c_time" in df.columns else pd.Series([None] * total)
    if not dates.any():
        dates = (df["crawl_at"].apply(_to_date)
                 if "crawl_at" in df.columns else pd.Series([None] * total))
    time_dist = _build_time_dist(dates)

    # 最近一次入库时间
    latest_crawl_at = None
    if "crawl_at" in df.columns:
        non_null = df["crawl_at"].dropna()
        if not non_null.empty:
            latest_crawl_at = str(non_null.max())

    # 词云数据
    wordcloud_data = get_word_freq(df["content"], top_n=top_n)

    return {
        "total": total,
        "domestic_total": domestic_total,
        "overseas_total": overseas_total,
        "total_videos": int(df["bv"].nunique()),
        "total_users": int(df["user_id"].nunique()),
        "region_dist": region_dist,
        "top_users": top_users,
        "top_videos": top_videos,
        "time_dist": time_dist,
        "wordcloud_data": wordcloud_data,
        "latest_crawl_at": latest_crawl_at,
    }


def query_comments(
    collection,
    bv: Optional[str] = None,
    keyword: Optional[str] = None,
    user: Optional[str] = None,
    region: Optional[str] = None,
    sort: str = "time",
    page: int = 1,
    page_size: int = 20,
) -> Dict:
    """
    分页查询评论，支持多条件过滤。

    过滤条件：
      - bv:     视频 BV 号（精确匹配）
      - keyword: 评论内容关键词（模糊匹配）
      - user:    用户昵称关键词（模糊匹配）
      - region:  地区，支持 国内 / 海外 / 具体地区名（如 上海）

    返回 {total, page, page_size, items}。
    """
    filters: Dict = {}
    if bv:
        filters["bv"] = bv
    if keyword:
        filters["content"] = {"$regex": re.escape(keyword), "$options": "i"}
    if user:
        filters["user_name"] = {"$regex": re.escape(user), "$options": "i"}
    if region:
        if region == "国内":
            filters.update(domestic_filter(True))
        elif region == "海外":
            filters.update(domestic_filter(False))
        else:
            filters["ip"] = {"$regex": "^" + re.escape(region)}

    if sort == "time":
        sort_key = [("c_time", -1), ("_id", -1)]
    else:
        sort_key = [("_id", -1)]

    total = collection.count_documents(filters)
    cursor = (
        collection.find(filters, {"_id": 0})
        .sort(sort_key)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    items = list(cursor)

    # 兼容旧数据：无 c_time 时展示为空
    for item in items:
        item.setdefault("c_time", None)
        item.setdefault("crawl_at", None)

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }


def list_videos(collection, limit: int = 100) -> List[Dict]:
    """
    按评论数统计视频排行，返回 [{bv, count, latest_c_time, latest_crawl_at}]。
    """
    pipeline = [
        {"$group": {
            "_id": "$bv",
            "count": {"$sum": 1},
            "latest_c_time": {"$max": "$c_time"},
            "latest_crawl_at": {"$max": "$crawl_at"},
        }},
        {"$sort": {"count": -1}},
        {"$limit": limit},
    ]
    result = []
    for row in collection.aggregate(pipeline):
        result.append({
            "bv": row["_id"],
            "count": row["count"],
            "latest_c_time": row.get("latest_c_time"),
            "latest_crawl_at": row.get("latest_crawl_at"),
        })
    return result
