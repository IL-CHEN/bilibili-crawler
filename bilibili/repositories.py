from pathlib import Path
from typing import List, Dict

import pandas as pd

from bilibili.interfaces import Repository


class FileRepository(Repository):
    """文件存储实现"""

    def __init__(self, bv_file: str, comment_dir: str):
        self.bv_file = bv_file
        self.comment_dir = Path(comment_dir)
        self.comment_dir.mkdir(parents=True, exist_ok=True)

    def save_bvs(self, bvs: List[str]) -> None:
        with open(self.bv_file, 'a', encoding='utf-8') as f:
            f.write('\n'.join(bvs) + '\n')
        print(f"BV 写入文件: {self.bv_file}")

    def save_comments(self, comments: List[Dict]) -> None:
        if not comments:
            return
        df = pd.DataFrame(comments)
        path = self.comment_dir / 'comments.csv'
        if path.exists():
            df.to_csv(path, mode='a', encoding='utf-8-sig', header=False, index=False)
        else:
            df.to_csv(path, mode='w', encoding='utf-8-sig', header=True, index=False)
        print(f"评论追加到文件: {path}")


class MongoRepository(Repository):
    """MongoDB 存储实现"""

    def __init__(self, connection_string: str, db_name: str):
        self.client = __import__('pymongo').MongoClient(connection_string)
        self.db = self.client[db_name]

    def save_bvs(self, bvs: List[str]) -> None:
        # BV 存储不在 MongoDB 中实现，留空
        pass

    def save_comments(self, comments: List[Dict]) -> None:
        if not comments:
            return
        # 补充视频网址字段
        for c in comments:
            if 'bv' in c and 'video_url' not in c:
                c['video_url'] = f"https://www.bilibili.com/video/{c['bv']}"
        collection = self.db['comments']
        for comment in comments:
            collection.update_one(
                {'bv': comment['bv'], 'rp_id': comment['rp_id']},
                {'$set': comment},
                upsert=True
            )
        print(f"已通过 MongoDB 保存/更新 {len(comments)} 条评论")
