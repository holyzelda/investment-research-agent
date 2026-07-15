"""数据库基础设施：ORM 声明基类。

Base 是所有 ir_agent ORM 模型的基类。各模块的 ORM 在其 persistence 包内定义并
自注册进 Base.metadata（导入即注册），本包不再集中汇总——避免 __init__ 与
orm 之间的循环导入。建表 DDL 由 ORM 生成（见 sql/ir_agent_schema.sql）。
"""
from app.infrastructure.database.base import Base

__all__ = ["Base"]
