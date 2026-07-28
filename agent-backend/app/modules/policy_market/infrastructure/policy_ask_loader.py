"""Deferred loading for the heavy policy knowledge-base SDK."""
from __future__ import annotations

import asyncio
import importlib
from types import ModuleType

_warmup_task: asyncio.Task[ModuleType] | None = None


async def _import_policy_ask() -> ModuleType:
    return await asyncio.to_thread(importlib.import_module, "tools.policy_ask")


def start_policy_ask_warmup() -> asyncio.Task[ModuleType]:
    """Start one shared background import and return its task."""
    global _warmup_task
    if _warmup_task is None:
        _warmup_task = asyncio.create_task(
            _import_policy_ask(), name="policy-ask-sdk-warmup"
        )
    return _warmup_task


async def get_policy_ask_module() -> ModuleType:
    """Wait for the shared warm-up task and return the policy script module."""
    return await start_policy_ask_warmup()


async def stop_policy_ask_warmup() -> None:
    """Cancel an unfinished warm-up task during application shutdown."""
    global _warmup_task
    task = _warmup_task
    _warmup_task = None
    if task is not None and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
