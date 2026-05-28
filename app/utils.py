"""项目公共工具函数。"""

import datetime


def now_str() -> str:
    """返回当前时间的格式化字符串（%Y-%m-%d %H:%M:%S）。"""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
