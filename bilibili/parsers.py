from typing import List, Dict

from bilibili.interfaces import CommentParser


class BilibiliCommentParser(CommentParser):
    """B 站评论报文解析器"""

    @staticmethod
    def _parse_reply(reply: dict) -> dict:
        user_id = str(reply['member']['mid'])
        user_name = reply['member']['uname']
        content = reply['content']['message']
        rp_id = str(reply['rpid'])
        ip = ''
        if reply.get('reply_control') and reply['reply_control'].get('location'):
            ip = reply['reply_control']['location'].split('：')[-1]
        return {
            'rp_id': rp_id,
            'user_id': user_id,
            'user_name': user_name,
            'content': content,
            'ip': ip,
            'c_time': reply.get('ctime', 0),
        }

    def parse_main(self, response: dict) -> tuple:
        replies = response['data']['replies']
        if not replies:
            return [], []
        comments = []
        need_sub_rpids = []
        for reply in replies:
            comments.append(self._parse_reply(reply))
            if reply['replies']:
                need_sub_rpids.append(str(reply['rpid']))
        return comments, need_sub_rpids

    def parse_sub(self, response: dict) -> List[Dict]:
        replies = response['data']['replies']
        if not replies:
            return []
        return [self._parse_reply(reply) for reply in replies]
