"""平台接入上下文 · 领域模型（无框架依赖）。"""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CurrentUser:
    """当前用户（值对象）：由平台身份中间件从请求头解析后放入 request.state。

    阶段0 不做登录，仅取 user_id/username 用于快照归属。
    """
    user_id: Optional[str]
    username: Optional[str]
