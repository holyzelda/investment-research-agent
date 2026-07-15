"""副本命名 build_copy_name · 单测（城市-节点-功率/容量-时间到秒）。"""
from datetime import datetime

from app.modules.calculation.application.task_service import build_copy_name
from app.modules.calculation.domain.models import ProjectBasics

_NOW = datetime(2026, 7, 10, 9, 14, 35)


def test_name_without_node():
    n = build_copy_name(ProjectBasics(province="宁夏", capacity_mwh=400, power_mw=200), now=_NOW)
    assert n == "宁夏-200/400-20260710091435"


def test_name_with_node():
    b = ProjectBasics(province="宁夏", capacity_mwh=400, power_mw=200, node_name="东站")
    assert build_copy_name(b, now=_NOW) == "宁夏-东站-200/400-20260710091435"


def test_integer_floats_have_no_dot_zero():
    b = ProjectBasics(province="甘肃", capacity_mwh=800.0, power_mw=200.0)
    assert build_copy_name(b, now=_NOW) == "甘肃-200/800-20260710091435"


def test_non_integer_capacity_kept():
    b = ProjectBasics(province="甘肃", capacity_mwh=800.5, power_mw=200)
    assert build_copy_name(b, now=_NOW) == "甘肃-200/800.5-20260710091435"


def test_empty_node_is_omitted():
    b = ProjectBasics(province="宁夏", capacity_mwh=400, power_mw=200, node_name="")
    assert build_copy_name(b, now=_NOW) == "宁夏-200/400-20260710091435"
