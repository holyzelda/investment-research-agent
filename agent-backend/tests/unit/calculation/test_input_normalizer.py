"""测算任务 HTTP 输入的规模归一化测试。"""

import pytest

from app.core.exceptions import ValidationException
from app.modules.calculation.application.input_normalizer import normalize_project_basics


def normalize(*, capacity_mwh=None, power_mw=None, duration_hours=None):
    return normalize_project_basics(
        province="甘肃",
        capacity_mwh=capacity_mwh,
        power_mw=power_mw,
        duration_hours=duration_hours,
        node_name="兰州东",
        voltage_kv=220,
    )


def test_keeps_explicit_capacity_and_power():
    basics = normalize(capacity_mwh=800, power_mw=200)

    assert basics.province == "甘肃"
    assert basics.capacity_mwh == 800
    assert basics.power_mw == 200
    assert basics.node_name == "兰州东"
    assert basics.voltage_kv == 220


def test_derives_capacity_from_power_and_duration():
    basics = normalize(power_mw=100, duration_hours=2)

    assert basics.power_mw == 100
    assert basics.capacity_mwh == 200


def test_derives_power_from_capacity_and_duration():
    basics = normalize(capacity_mwh=400, duration_hours=4)

    assert basics.capacity_mwh == 400
    assert basics.power_mw == 100


def test_uses_default_power_for_duration_only():
    basics = normalize(duration_hours=2)

    assert basics.power_mw == 100
    assert basics.capacity_mwh == 200


def test_accepts_all_three_when_consistent():
    basics = normalize(capacity_mwh=200, power_mw=100, duration_hours=2)

    assert basics.capacity_mwh == 200
    assert basics.power_mw == 100


@pytest.mark.parametrize(
    ("capacity_mwh", "power_mw", "duration_hours", "message"),
    [
        (150, 100, 2, "不一致"),
        (None, 100, None, "容量和功率"),
        (200, None, None, "容量和功率"),
        (None, None, None, "容量和功率"),
    ],
)
def test_rejects_invalid_size_combinations(
    capacity_mwh, power_mw, duration_hours, message
):
    with pytest.raises(ValidationException, match=message):
        normalize(
            capacity_mwh=capacity_mwh,
            power_mw=power_mw,
            duration_hours=duration_hours,
        )
