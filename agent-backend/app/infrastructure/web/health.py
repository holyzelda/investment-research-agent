"""Web 基础设施：健康检查路由。"""
from fastapi import APIRouter

from app.core.response import ok

router = APIRouter()


@router.get("/health", tags=["system"])
async def health():
    return ok({"status": "up"})
