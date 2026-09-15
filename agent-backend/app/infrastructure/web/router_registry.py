"""路由集中注册：挂载各限界上下文的 interface 路由。"""
from fastapi import FastAPI

from app.infrastructure.web.health import router as system_router
from app.modules.calculation.interface.router import router as calculation_router
from app.modules.calculation.interface.conversation_router import router as conversation_router
from app.modules.calculation.interface.ledger_router import router as calculation_ledger_router
from app.modules.calculation.interface.share_router import router as calculation_share_router
from app.modules.platform_access.interface.router import router as platform_access_router
from app.modules.index_map.interface.router import router as index_map_router
from app.modules.tie_line_map.interface.router import router as tie_line_router
from app.modules.trial_quota.interface.router import router as trial_quota_router


def register_routers(app: FastAPI) -> None:
    app.include_router(system_router)
    app.include_router(platform_access_router)
    # 台账路由先于 calculation_router：避免 /ir/calc/ledger 被 /ir/calc/tasks/{task_id} 之外的通配吸收
    app.include_router(calculation_ledger_router)
    app.include_router(calculation_router)
    app.include_router(conversation_router)
    app.include_router(calculation_share_router)
    app.include_router(tie_line_router)
    app.include_router(index_map_router)
    app.include_router(trial_quota_router)
