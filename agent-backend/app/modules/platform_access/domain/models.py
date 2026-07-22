"""平台接入上下文 · 领域模型（无框架依赖）。"""
from dataclasses import dataclass


@dataclass(frozen=True)
class CurrentUser:
    """当前用户：由平台身份中间件从固定 Header 解析后放入 request.state。"""

    user_id: str
    username: str
