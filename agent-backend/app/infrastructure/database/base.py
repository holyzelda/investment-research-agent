"""ORM 声明基类。所有 ir_agent 模型继承 Base（Batch 3 起新增快照/会话/任务表）。"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
