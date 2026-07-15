"""domain/services 两档收益插值 · 纯逻辑单测（TDD）。

用例覆盖：
- t<2 / 2≤t≤4 / t>4 三段分支
- 中长期(容量型)、调频(功率型)、干预(容量型)三个公式
- 两档缺失返回 None
以宁夏两档为基准数据（表2：中长期240/480，调频700/960，干预330/540）。
"""
import pytest

from app.modules.calculation.domain.models import TwoTier
from app.modules.calculation.domain.services import (
    frequency_first_year_revenue,
    intervention_first_year_revenue,
    mid_long_first_year_revenue,
)

NX_MID = TwoTier(240, 480)   # 宁夏中长期 C/D
NX_FREQ = TwoTier(700, 960)  # 宁夏调频 G/H
NX_INT = TwoTier(330, 540)   # 宁夏干预 O/P


class TestMidLong:
    def test_duration_lt_2(self):
        # t=1: base=t2=240; 容量系数=容量/200=100/200=0.5 → 120
        assert mid_long_first_year_revenue(NX_MID, capacity_mwh=100, power_mw=100) == pytest.approx(120.0)

    def test_duration_between_2_and_4(self):
        # t=2 (200/100): base=240+(480-240)*(2-2)/2=240; 系数=200/(100*2)=1 → 240
        assert mid_long_first_year_revenue(NX_MID, capacity_mwh=200, power_mw=100) == pytest.approx(240.0)

    def test_duration_eq_3(self):
        # t=3 (300/100): base=240+(240)*(3-2)/2=360; 系数=300/(100*3)=1 → 360
        assert mid_long_first_year_revenue(NX_MID, capacity_mwh=300, power_mw=100) == pytest.approx(360.0)

    def test_duration_gt_4(self):
        # t=5 (500/100): base=480+(480-240)*(5-4)/2=600; 系数=500/(100*5)=1 → 600
        assert mid_long_first_year_revenue(NX_MID, capacity_mwh=500, power_mw=100) == pytest.approx(600.0)

    def test_tier_missing_returns_none(self):
        assert mid_long_first_year_revenue(TwoTier(None, None), 200, 100) is None


class TestFrequency:
    def test_duration_lt_2(self):
        # t=1: base=700*(1/2)=350; 功率系数=功率/100=100/100=1 → 350
        assert frequency_first_year_revenue(NX_FREQ, capacity_mwh=100, power_mw=100) == pytest.approx(350.0)

    def test_duration_between_2_and_4(self):
        # t=3 (300/100): base=700+(960-700)*(3-2)/2=830; 功率系数=100/100=1 → 830
        assert frequency_first_year_revenue(NX_FREQ, capacity_mwh=300, power_mw=100) == pytest.approx(830.0)

    def test_duration_gt_4(self):
        # t=5 (1000/200): base=h=960; 功率系数=200/100=2 → 1920
        assert frequency_first_year_revenue(NX_FREQ, capacity_mwh=1000, power_mw=200) == pytest.approx(1920.0)

    def test_tier_missing_returns_none(self):
        assert frequency_first_year_revenue(TwoTier(None, None), 200, 100) is None


class TestIntervention:
    def test_capacity_type_same_as_mid_long_shape(self):
        # t=1: base=330; 系数=100/200=0.5 → 165
        assert intervention_first_year_revenue(NX_INT, capacity_mwh=100, power_mw=100) == pytest.approx(165.0)

    def test_duration_gt_4(self):
        # t=5: base=540+(540-330)*(5-4)/2=645; 系数=500/(100*5)=1 → 645
        assert intervention_first_year_revenue(NX_INT, capacity_mwh=500, power_mw=100) == pytest.approx(645.0)
