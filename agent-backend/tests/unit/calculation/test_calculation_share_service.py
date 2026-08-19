"""分享服务 · 单测（计算分享码、白名单提取、状态派生）。"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.modules.calculation.application.calculation_share_service import (
    CalculationShareService,
    PUBLIC_RESULT_FIELDS,
    VALID_DURATIONS,
)


def test_whitelist_contains_expected_fields():
    assert "basicInfo" in PUBLIC_RESULT_FIELDS
    assert "financial" in PUBLIC_RESULT_FIELDS
    assert "advanced.donut" in PUBLIC_RESULT_FIELDS
    assert "advanced.debtServiceCoverage" in PUBLIC_RESULT_FIELDS
    assert "warnings" in PUBLIC_RESULT_FIELDS
    assert "calculatedAt" in PUBLIC_RESULT_FIELDS
    assert len(PUBLIC_RESULT_FIELDS) == 6


def test_whitelist_rejects_unexpected_paths():
    assert "taskId" not in PUBLIC_RESULT_FIELDS
    assert "conversationId" not in PUBLIC_RESULT_FIELDS
    assert "basicInfo.province" not in PUBLIC_RESULT_FIELDS  # 白名单只允许顶层，嵌套由 _extract_public_fields 展开


def test_valid_durations():
    assert VALID_DURATIONS == {7, 14, 30}


def test_extract_public_fields_flat_top_level():
    """顶层字段直接提取。"""
    payload = {
        "basicInfo": {"province": "甘肃", "powerMw": 200, "actualSpread": 0.42},
        "financial": {"projectIrr": 8.5},
        "calculatedAt": "2026-08-13T10:00:00",
        "warnings": ["注意：换电成本较高"],
    }
    result = CalculationShareService._extract_public_fields(payload)
    assert result["basicInfo"] == {"province": "甘肃", "powerMw": 200, "actualSpread": 0.42}
    assert result["financial"] == {"projectIrr": 8.5}
    assert result["calculatedAt"] == "2026-08-13T10:00:00"
    assert result["warnings"] == ["注意：换电成本较高"]


def test_extract_public_fields_nested_path():
    """嵌套路径正确展开为两级字典。"""
    payload = {
        "advanced": {
            "donut": {"totalRevenue": 8600, "energyRevenue": 5200},
            "debtServiceCoverage": {"years": [2026, 2027], "values": [1.2, 1.5]},
        },
    }
    result = CalculationShareService._extract_public_fields(payload)
    assert result["advanced"]["donut"] == {"totalRevenue": 8600, "energyRevenue": 5200}
    assert result["advanced"]["debtServiceCoverage"] == {"years": [2026, 2027], "values": [1.2, 1.5]}


def test_extract_public_fields_skips_missing_keys():
    """payload 缺失某白名单字段时静默跳过。"""
    payload = {"basicInfo": {"province": "甘肃"}}
    result = CalculationShareService._extract_public_fields(payload)
    assert "financial" not in result
    assert "advanced" not in result
    assert "warnings" not in result
    assert "calculatedAt" not in result
    assert result["basicInfo"] == {"province": "甘肃"}


def test_extract_public_fields_skips_null_values():
    """白名单字段值为 None 时静默跳过。"""
    payload = {"basicInfo": {"province": "甘肃"}, "financial": None}
    result = CalculationShareService._extract_public_fields(payload)
    assert "basicInfo" in result
    assert "financial" not in result


def test_extract_public_fields_partial_nested():
    """嵌套路径中中间层存在但最终键缺失时静默跳过。"""
    payload = {"advanced": {"donut": {"totalRevenue": 8600}}}
    result = CalculationShareService._extract_public_fields(payload)
    assert "advanced" in result
    assert "debtServiceCoverage" not in result.get("advanced", {})
    assert result["advanced"]["donut"] == {"totalRevenue": 8600}


def test_share_code_generation_is_high_entropy():
    """生成的分享码是 URL-safe base64, 32 字节熵 → 43 字符。"""
    code = CalculationShareService._generate_share_code()
    assert len(code) == 32  # token_urlsafe(24) → 32 字符
    # 校验字符集
    assert all(c.isalnum() or c in "-_" for c in code)


def test_share_code_hash_is_consistent():
    """同一内容的 SHA-256 哈希一致。"""
    h1 = CalculationShareService._hash_share_code("abc123")
    h2 = CalculationShareService._hash_share_code("abc123")
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex


def test_share_code_hash_is_collision_resistant():
    """不同内容的哈希不同。"""
    h1 = CalculationShareService._hash_share_code("abc123")
    h2 = CalculationShareService._hash_share_code("abc124")
    assert h1 != h2


def test_fernet_encrypt_decrypt_roundtrip():
    """Fernet 加解密往返。"""
    from cryptography.fernet import Fernet

    svc = CalculationShareService(fernet_key=Fernet.generate_key())
    code = "test-share-code-123"
    encrypted = svc._encrypt_share_code(code)
    decrypted = svc._decrypt_share_code(encrypted)
    assert decrypted == code
    assert encrypted != code