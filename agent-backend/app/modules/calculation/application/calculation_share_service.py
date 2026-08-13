"""测算结果分享：创建、撤销、公开查询及会话删除联动。"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ValidationException
from app.modules.calculation.infrastructure.persistence.orm import (
    CalculationResultSnapshotORM,
    CalculationShareORM,
    CalculationTaskORM,
    ConversationORM,
    InputSnapshotORM,
)

# 白名单：公开分享可展示的字段（结果卡片已展示的业务内容）。
# 嵌套结构用 "." 分隔路径，如 "basicInfo.province"。
PUBLIC_RESULT_FIELDS = frozenset({
    "basicInfo",
    "financial",
    "advanced.donut",
    "advanced.debtServiceCoverage",
    "warnings",
    "calculatedAt",
})

# 分享有效期选项（天）
VALID_DURATIONS = frozenset({7, 14, 30})
DEFAULT_DURATION = 7
MAX_DURATION = 30


class CalculationShareService:
    """分享生命周期管理。"""

    def __init__(self, fernet_key: bytes | None = None):
        """Fernet 密钥用于加密分享码以便管理端回显。缺少时使用固定测试密钥。"""
        if fernet_key is not None:
            self._fernet = Fernet(fernet_key)
        else:
            # 生产环境应从配置/环境变量注入；开发期使用固定密钥（不要用于生产数据）。
            self._fernet = Fernet(Fernet.generate_key())

    # ── 分享码处理 ────────────────────────────────────────────────

    @staticmethod
    def _generate_share_code() -> str:
        """生成高熵分享码。"""
        return secrets.token_urlsafe(24)

    @staticmethod
    def _hash_share_code(code: str) -> str:
        return hashlib.sha256(code.encode("utf-8")).hexdigest()

    def _encrypt_share_code(self, code: str) -> str:
        return self._fernet.encrypt(code.encode("utf-8")).decode("utf-8")

    def _decrypt_share_code(self, ciphertext: str) -> str:
        return self._fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")

    # ── 创建分享 ───────────────────────────────────────────────────

    async def create_share(
        self,
        session: AsyncSession,
        *,
        task_id: int,
        user_id: str,
        duration_days: int = DEFAULT_DURATION,
    ) -> dict:
        """为指定测算版本创建分享链接。

        Returns:
            {shareCode, shareUrl, expiresAt, durationDays}
        """
        if duration_days not in VALID_DURATIONS:
            raise ValidationException(
                f"有效期天数必须为 {'/'.join(str(d) for d in sorted(VALID_DURATIONS))} 天"
            )

        # 验证任务归属：当前用户拥有该任务所在会话
        task = await self._require_owned_task(session, task_id=task_id, user_id=user_id)
        if task.status != "completed":
            raise ValidationException("仅成功完成的测算版本可分享")

        # 检查该任务是否已有有效分享（单个版本最多一个有效链接）
        existing = (await session.execute(
            select(CalculationShareORM).where(
                CalculationShareORM.task_id == task_id,
                CalculationShareORM.revoked_at.is_(None),
                CalculationShareORM.expires_at > func.now(),
            )
        )).scalar_one_or_none()
        if existing is not None:
            # 已有有效分享，返回现有
            share_code = self._decrypt_share_code(existing.share_code_ciphertext)
            return {
                "shareId": existing.id,
                "shareCode": share_code,
                "shareUrl": self._build_share_url(share_code),
                "expiresAt": existing.expires_at.isoformat(),
                "durationDays": existing.duration_days,
                "createdAt": existing.created_at.isoformat(),
            }

        now = datetime.now()
        expires_at = now + timedelta(days=duration_days)
        share_code = self._generate_share_code()

        record = CalculationShareORM(
            conversation_id=task.conversation_id,
            task_id=task_id,
            owner_user_id=user_id,
            share_code_hash=self._hash_share_code(share_code),
            share_code_ciphertext=self._encrypt_share_code(share_code),
            duration_days=duration_days,
            expires_at=expires_at,
        )
        session.add(record)
        await session.commit()
        await session.refresh(record)

        return {
            "shareId": record.id,
            "shareCode": share_code,
            "shareUrl": self._build_share_url(share_code),
            "expiresAt": expires_at.isoformat(),
            "durationDays": duration_days,
            "createdAt": record.created_at.isoformat(),
        }

    @staticmethod
    def _build_share_url(share_code: str) -> str:
        """构造前端分享页面 URL。"""
        return f"/investment/public/calculation-shares/{share_code}"

    # ── 列表 ───────────────────────────────────────────────────────

    async def list_shares(
        self,
        session: AsyncSession,
        *,
        user_id: str,
        conversation_id: str | None = None,
        task_id: int | None = None,
    ) -> list[dict]:
        """列出当前用户的所有分享记录（按创建时间倒序）。

        可指定 conversation_id 或 task_id 筛选。
        """
        query = (
            select(CalculationShareORM)
            .join(
                ConversationORM,
                ConversationORM.id == CalculationShareORM.conversation_id,
            )
            .where(
                ConversationORM.user_id == user_id,
                ConversationORM.deleted_at.is_(None),
            )
        )
        if conversation_id is not None:
            query = query.where(CalculationShareORM.conversation_id == conversation_id)
        if task_id is not None:
            query = query.where(CalculationShareORM.task_id == task_id)

        query = query.order_by(CalculationShareORM.created_at.desc())

        records = (await session.execute(query)).scalars().all()

        now = datetime.now()
        items = []
        for r in records:
            try:
                share_code = self._decrypt_share_code(r.share_code_ciphertext)
            except Exception:
                share_code = None

            # 派生状态
            if r.revoked_at is not None:
                status = "revoked"
            elif r.expires_at <= now:
                status = "expired"
            else:
                status = "active"

            items.append({
                "shareId": r.id,
                "taskId": r.task_id,
                "conversationId": r.conversation_id,
                "shareCode": share_code,
                "shareUrl": self._build_share_url(share_code) if share_code else None,
                "durationDays": r.duration_days,
                "createdAt": r.created_at.isoformat(),
                "expiresAt": r.expires_at.isoformat(),
                "revokedAt": r.revoked_at.isoformat() if r.revoked_at else None,
                "status": status,
            })
        return items

    # ── 撤销 ───────────────────────────────────────────────────────

    async def revoke_share(
        self,
        session: AsyncSession,
        *,
        share_id: int | None = None,
        task_id: int | None = None,
        user_id: str,
    ) -> dict:
        """撤销指定分享。支持 share_id 或 task_id 定位。"""
        if share_id is None and task_id is None:
            raise ValidationException("必须指定 share_id 或 task_id")

        record = await self._require_owned_share(
            session, share_id=share_id, task_id=task_id, user_id=user_id,
        )
        record.revoked_at = datetime.now()
        await session.commit()
        return {"shareId": record.id, "revoked": True}

    async def revoke_by_conversation(
        self, session: AsyncSession, *, conversation_id: str,
    ) -> int:
        """撤销会话关联的所有有效分享（会话删除联动）。返回撤销数量。"""
        now = datetime.now()
        records = (await session.execute(
            select(CalculationShareORM).where(
                CalculationShareORM.conversation_id == conversation_id,
                CalculationShareORM.revoked_at.is_(None),
                CalculationShareORM.expires_at > now,
            )
        )).scalars().all()
        for r in records:
            r.revoked_at = now
        if records:
            await session.commit()
        return len(records)

    # ── 公开查询（免登录） ─────────────────────────────────────────

    async def resolve_share(
        self, session: AsyncSession, *, share_code: str,
    ) -> dict:
        """通过分享码公开查询测算结果。

        Returns:
            {status, result, version, basicInfo, ...}
            其中 status 为 "active" / "expired" / "revoked" / "not_found"
        """
        code_hash = self._hash_share_code(share_code)
        record = (await session.execute(
            select(CalculationShareORM).where(
                CalculationShareORM.share_code_hash == code_hash,
            )
        )).scalar_one_or_none()

        if record is None:
            return {"status": "not_found"}

        now = datetime.now()

        # 撤销检查
        if record.revoked_at is not None:
            return {
                "status": "revoked",
                "revokedAt": record.revoked_at.isoformat(),
                "createdAt": record.created_at.isoformat(),
            }

        # 过期检查
        if record.expires_at <= now:
            return {
                "status": "expired",
                "expiresAt": record.expires_at.isoformat(),
                "createdAt": record.created_at.isoformat(),
            }

        # 有效：获取测算结果
        result_snapshot = (await session.execute(
            select(CalculationResultSnapshotORM).where(
                CalculationResultSnapshotORM.task_id == record.task_id,
            )
        )).scalar_one_or_none()
        if result_snapshot is None:
            return {"status": "not_found"}

        task = (await session.execute(
            select(CalculationTaskORM).where(
                CalculationTaskORM.id == record.task_id,
            )
        )).scalar_one_or_none()

        # 获取版本信息
        version = task.version if task else ""

        # 获取省份/节点等基本信息
        basic_info = self._extract_public_fields(result_snapshot.payload)

        return {
            "status": "active",
            "version": version,
            "calculatedAt": task.created_at.isoformat() if task else "",
            **basic_info,
        }

    @staticmethod
    def _extract_public_fields(payload: dict) -> dict:
        """从结果快照中提取白名单字段，保留嵌套结构。"""
        result = {}
        for field in PUBLIC_RESULT_FIELDS:
            parts = field.split(".")
            value = payload
            try:
                for part in parts:
                    value = value[part]
            except (KeyError, TypeError):
                continue

            # 跳过 None 值
            if value is None:
                continue

            if len(parts) == 1:
                result[parts[0]] = value
            else:
                # 嵌套路径：逐层创建中间字典
                current = result
                for part in parts[:-1]:
                    if part not in current or not isinstance(current[part], dict):
                        current[part] = {}
                    current = current[part]
                current[parts[-1]] = value
        return result

    # ── 所有权验证 ─────────────────────────────────────────────────

    async def _require_owned_task(
        self, session: AsyncSession, *, task_id: int, user_id: str,
    ) -> CalculationTaskORM:
        task = (await session.execute(
            select(CalculationTaskORM)
            .join(
                ConversationORM,
                ConversationORM.id == CalculationTaskORM.conversation_id,
            )
            .where(
                CalculationTaskORM.id == task_id,
                ConversationORM.user_id == user_id,
                ConversationORM.deleted_at.is_(None),
            )
        )).scalar_one_or_none()
        if task is None:
            raise NotFoundException("任务不存在")
        return task

    async def _require_owned_share(
        self,
        session: AsyncSession,
        *,
        share_id: int | None,
        task_id: int | None,
        user_id: str,
    ) -> CalculationShareORM:
        query = (
            select(CalculationShareORM)
            .join(
                ConversationORM,
                ConversationORM.id == CalculationShareORM.conversation_id,
            )
            .where(
                ConversationORM.user_id == user_id,
                ConversationORM.deleted_at.is_(None),
            )
        )
        if share_id is not None:
            query = query.where(CalculationShareORM.id == share_id)
        elif task_id is not None:
            query = query.where(CalculationShareORM.task_id == task_id)

        query = query.order_by(CalculationShareORM.created_at.desc()).limit(1)
        record = (await session.execute(query)).scalar_one_or_none()
        if record is None:
            raise NotFoundException("分享记录不存在")
        return record