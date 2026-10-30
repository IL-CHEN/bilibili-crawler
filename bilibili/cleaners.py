import re

from bilibili.interfaces import Cleaner


class DefaultCleaner(Cleaner):
    """默认清洗器：去除回复抬头、表情标签、空白字符"""

    def clean(self, text: str) -> str:
        if not text:
            return ""
        # 提取回复内容（去除“回复 @xxx :”）
        match = re.search(r'回复 @[^:]+:\s*(.*)', text)
        text = match.group(1) if match else text
        # 删除 [xxx] 表情标签
        text = re.sub(r'\[.*?]', '', text)
        # 删除换行、回车、所有空格
        # text = re.sub(r'[\n\r\s]+', '', text)
        return text.strip()
