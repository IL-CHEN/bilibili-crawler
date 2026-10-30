import re
from typing import Set

from bilibili.interfaces import Extractor

# 兼容两种页面形态：
#   JSON:   "bvid":"BV1FW9ZBhExc"
#   JS:     bvid:"BV1FW9ZBhExc"
# B 站 BV 号规范：BV + 10 位字母数字
_BV_PATTERN = r'bvid["\']?\s*[:=]\s*["\']*(BV[0-9A-Za-z]{10})'


class RegexBvExtractor(Extractor):
    """正则提取 B 站 BV 号"""

    def extract(self, html: str) -> Set[str]:
        bvs = re.findall(_BV_PATTERN, html, re.S)
        print(f"提取到 {len(bvs)} 条 BV 号")
        return set(bvs)
