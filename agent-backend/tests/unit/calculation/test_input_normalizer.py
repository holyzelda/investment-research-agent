"""测算任务 HTTP 输入的规模归一化测试。"""

import pytest

from app.core.exceptions import ValidationException
from app.modules.calculation.application.input_normalizer import (
    complete_scale_anchors,
    normalize_project_basics,
)


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
    ("capacity_mwh", "power_mw", "duration_hours"),
    [(300, 100, None), (None, None, 3), (100, 100, 1)],
)
def test_rejects_system_durations_other_than_two_or_four_hours(
    capacity_mwh, power_mw, duration_hours
):
    with pytest.raises(ValidationException, match="仅支持2小时或4小时"):
        normalize(
            capacity_mwh=capacity_mwh,
            power_mw=power_mw,
            duration_hours=duration_hours,
        )


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


_PREV = {"capacity_mwh": 800, "power_mw": 200, "duration_hours": 4}


def test_no_previous_input_returns_as_is():
    assert complete_scale_anchors(
        previous_input=None, capacity_mwh=400, power_mw=None, duration_hours=None,
    ) == (400, None, None)


def test_only_power_changed_keeps_previous_capacity():
    """改功率不改容量：容量沿用上一版（改功率=改时长，200/800→400/800 变 2h 系统）。"""
    cap, pwr, dur = complete_scale_anchors(
        previous_input=_PREV, capacity_mwh=None, power_mw=400, duration_hours=None,
    )
    assert cap == 800
    assert pwr == 400
    assert dur is None


def test_only_capacity_changed_keeps_previous_power():
    cap, pwr, dur = complete_scale_anchors(
        previous_input=_PREV, capacity_mwh=1200, power_mw=None, duration_hours=None,
    )
    assert cap == 1200
    assert pwr == 200
    assert dur is None


def test_only_duration_changed_keeps_previous_capacity():
    """只改时长：容量沿用上一版，功率由 normalize 按容量/时长推导。"""
    cap, pwr, dur = complete_scale_anchors(
        previous_input=_PREV, capacity_mwh=None, power_mw=None, duration_hours=2,
    )
    assert cap == 800
    assert pwr is None
    assert dur == 2


def test_both_capacity_and_power_given_not_modified():
    cap, pwr, dur = complete_scale_anchors(
        previous_input=_PREV, capacity_mwh=900, power_mw=300, duration_hours=None,
    )
    assert (cap, pwr, dur) == (900, 300, None)


def test_capacity_and_duration_given_not_modified():
    """给了容量+时长（显式组合）→ 原样返回，normalize 推导功率。"""
    cap, pwr, dur = complete_scale_anchors(
        previous_input=_PREV, capacity_mwh=800, power_mw=None, duration_hours=4,
    )
    assert (cap, pwr, dur) == (800, None, 4)


def test_power_and_duration_given_not_modified():
    cap, pwr, dur = complete_scale_anchors(
        previous_input=_PREV, capacity_mwh=None, power_mw=200, duration_hours=4,
    )
    assert (cap, pwr, dur) == (None, 200, 4)


def test_no_scale_params_changed_inherits_all_previous():
    """本次只改节点/高级参数，规模参数全未提及 → 全部沿用上一版。"""
    cap, pwr, dur = complete_scale_anchors(
        previous_input=_PREV, capacity_mwh=None, power_mw=None, duration_hours=None,
    )
    assert (cap, pwr, dur) == (800, 200, 4)


def test_completion_feeds_normalize_for_power_only_change():
    """补全后交给 normalize：只改功率 400 → 得到 400/800（时长 2h 隐含）。"""
    cap, pwr, dur = complete_scale_anchors(
        previous_input=_PREV, capacity_mwh=None, power_mw=400, duration_hours=None,
    )
    basics = normalize_project_basics(
        province="甘肃", capacity_mwh=cap, power_mw=pwr, duration_hours=dur,
        node_name=None, voltage_kv=220,
    )
    assert basics.power_mw == 400
    assert basics.capacity_mwh == 800
