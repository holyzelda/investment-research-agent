"""现货电价多循环充放优化 · 单测。

核心正确性用穷举对照：`_simulate` 用领域自身的 `_transition` 回放动作串，保证穷举与 DP
共用同一套可行性/计分语义；再断言 DP 求得的最优 score 等于穷举最优 score。
另有若干场景断言（平价零动作、日初不能先放、min_run/switch_gap 生效、唯一最优精确匹配）。
"""
import itertools
import random
from decimal import Decimal

import pytest

from app.modules.calculation.domain import spot_pricing
from app.modules.calculation.domain.spot_pricing import (
    CHARGE,
    DISCHARGE,
    IDLE,
    PRECOMPUTE_K_VALUES,
    SpotConfig,
    _max_energy_slots,
    _min_run_slots,
    _switch_gap_slots,
    _terminal_ok,
    _transition,
    _NONE,
    day_optimal_by_k,
    k_from_inputs,
    optimize_day,
    optimize_day_dual_prices,
    yearly_average_prices,
)


def _cfg(cap="100", power="100", cycles="2", min_action=30, gap=15) -> SpotConfig:
    return SpotConfig(
        capacity_mwh=Decimal(cap), rated_power_mw=Decimal(power),
        max_equivalent_cycles=Decimal(cycles),
        min_action_minutes=min_action, switch_gap_minutes=gap,
    )


def _simulate(actions, prices, cfg):
    """回放动作串（复用领域 _transition）→ (score, slots, segments) 或 None（不可行）。"""
    K = _max_energy_slots(cfg, len(actions))
    mr, g = _min_run_slots(cfg), _switch_gap_slots(cfg)
    state, segs, score = (0, 0, _NONE), 0, Decimal(0)
    for i, a in enumerate(actions):
        res = _transition(state, a, K, mr, g)
        if res is None:
            return None
        ncc, ndc, nfsm, sd = res
        if a == CHARGE:
            score -= prices[i]
        elif a == DISCHARGE:
            score += prices[i]
        segs += sd
        state = (ncc, ndc, nfsm)
    cc, dc, fsm = state
    if cc != dc or not _terminal_ok(fsm, mr):
        return None
    return score, cc + dc, segs


def _brute(prices, cfg):
    """穷举所有动作串，取 (score 最大, 槽最少, 段最少) 的 key。"""
    best_key = None
    for combo in itertools.product((IDLE, CHARGE, DISCHARGE), repeat=len(prices)):
        r = _simulate(list(combo), prices, cfg)
        if r is None:
            continue
        score, slots, segs = r
        key = (score, -slots, -segs)
        if best_key is None or key > best_key:
            best_key = key
    return best_key  # 至少 (0, 0, 0)：全 IDLE 恒合法


# ---- 穷举对照：DP 最优 score 必等于穷举最优 score ----

@pytest.mark.parametrize("seed", range(25))
def test_dp_matches_bruteforce_score(seed):
    rnd = random.Random(seed)
    T = rnd.choice([6, 7, 8])
    prices = [Decimal(rnd.randint(-30, 100)) for _ in range(T)]
    cfg = _cfg(
        cycles=rnd.choice(["1", "2", "3"]),
        min_action=rnd.choice([15, 30]),
        gap=rnd.choice([0, 15, 30]),
    )
    dp = optimize_day(prices, cfg)
    dp_r = _simulate(dp, prices, cfg)
    assert dp_r is not None, "DP 产出的动作串必须可行"
    brute = _brute(prices, cfg)
    assert dp_r[0] == brute[0], f"score 不最优 seed={seed} prices={prices}"


# ---- 场景断言 ----

def test_flat_prices_choose_zero_action():
    dp = optimize_day([Decimal(5)] * 8, _cfg(min_action=15, gap=0))
    assert dp == [IDLE] * 8  # 无价差 → 零动作（最少槽平局规则）


def test_cannot_discharge_before_charging():
    # 高价在前、低价在后：想"先放高后充低"违反日初空仓不能放 → 无正价差 → 全 IDLE
    dp = optimize_day([Decimal(100), Decimal(1)], _cfg(min_action=15, gap=0))
    assert dp == [IDLE, IDLE]


def test_unique_optimum_charge_low_discharge_high():
    # [1,1,10,10]，K=2，min_run=1，gap=0 → 唯一最优 C,C,D,D
    dp = optimize_day([Decimal(1), Decimal(1), Decimal(10), Decimal(10)],
                      _cfg(cap="100", power="100", cycles="2", min_action=15, gap=0))
    assert dp == [CHARGE, CHARGE, DISCHARGE, DISCHARGE]


def test_dual_prices_use_charge_and_discharge_series_independently():
    cfg = _cfg(cap="100", power="100", cycles="2", min_action=15, gap=0)
    actions = optimize_day_dual_prices(
        [Decimal(10), Decimal(1)], [Decimal(10), Decimal(20)], cfg
    )
    assert actions == [CHARGE, DISCHARGE]


def test_dual_prices_require_equal_lengths():
    with pytest.raises(ValueError, match="长度必须一致"):
        optimize_day_dual_prices([Decimal(1)], [Decimal(1), Decimal(2)], _cfg())


def test_day_optimal_by_k_supports_dual_prices():
    prices = [Decimal(1), Decimal(10)] + [Decimal(0)] * 94
    discharge_prices = [Decimal(10), Decimal(20)] + [Decimal(0)] * 94
    result = day_optimal_by_k(
        prices, k_values=[1], min_action_minutes=15, switch_gap_minutes=0,
        discharge_prices=discharge_prices,
    )
    assert result[1] == (Decimal(1), Decimal(20), 1)


def test_min_run_blocks_single_slot_arbitrage():
    prices = [Decimal(1), Decimal(100)]
    # min_run=1（15min）：可 C@1→D@100，价差 99
    assert optimize_day(prices, _cfg(min_action=15, gap=0)) == [CHARGE, DISCHARGE]
    # min_run=2（30min）：单槽动作被禁、T=2 无法凑成平衡多槽 → 全 IDLE
    assert optimize_day(prices, _cfg(min_action=30, gap=0)) == [IDLE, IDLE]


def test_switch_gap_blocks_back_to_back_reversal():
    prices = [Decimal(1), Decimal(10), Decimal(1)]
    # gap=0：C@0 紧接 D@1，价差 9
    assert optimize_day(prices, _cfg(min_action=15, gap=0)) == [CHARGE, DISCHARGE, IDLE]
    # gap=15（1槽）：C→D 需先空闲 1 槽，错过高价 → 无正价差 → 全 IDLE
    assert optimize_day(prices, _cfg(min_action=15, gap=15)) == [IDLE, IDLE, IDLE]


def test_multi_cycle_charge_discharge_twice():
    # 两个明显的低-高对，K 足够 → 充放充放
    prices = [Decimal(1), Decimal(9), Decimal(1), Decimal(9)]
    dp = optimize_day(prices, _cfg(cap="100", power="100", cycles="3", min_action=15, gap=0))
    assert dp == [CHARGE, DISCHARGE, CHARGE, DISCHARGE]


# ---- 年度加权汇总 ----

def _day_cheap_then_dear():
    # 96 点：前 48 便宜(1)、后 48 贵(10)
    return [Decimal(1)] * 48 + [Decimal(10)] * 48


def test_yearly_weighted_average_and_skip_incomplete():
    cfg = _cfg(cap="100", power="100", cycles="1", min_action=30, gap=15)
    daily = {
        "d1": _day_cheap_then_dear(),
        "d2": _day_cheap_then_dear(),
        "d_bad": [Decimal(1)] * 50,   # 不足 96 点 → 跳过
    }
    avg_c, avg_d = yearly_average_prices(daily, cfg)
    assert avg_c == Decimal(1)      # 充电只会选到价=1 的槽
    assert avg_d == Decimal(10)     # 放电只会选到价=10 的槽


def test_yearly_none_when_no_opportunity():
    cfg = _cfg(min_action=30, gap=15)
    daily = {"flat": [Decimal(7)] * 96}
    assert yearly_average_prices(daily, cfg) == (None, None)


def test_yearly_none_when_all_days_incomplete():
    cfg = _cfg()
    assert yearly_average_prices({"x": [Decimal(1)] * 10}, cfg) == (None, None)


# ---- 预计算：k_from_inputs / day_optimal_by_k ----

def test_k_from_inputs_business_cases():
    # 时长2h(容量400/功率200) cycles=1 → floor(1×400/(200×0.25))=floor(8)=8
    assert k_from_inputs(Decimal(400), Decimal(200), Decimal("1")) == 8
    # 时长4h(容量800/功率200) cycles=2 → floor(2×800/50)=32
    assert k_from_inputs(Decimal(800), Decimal(200), Decimal("2")) == 32
    # cycles=1.2 时长2h → floor(1.2×8)=9
    assert k_from_inputs(Decimal(400), Decimal(200), Decimal("1.2")) == 9
    # 封顶 T/2=48（极端大容量）
    assert k_from_inputs(Decimal(100000), Decimal(100), Decimal("2")) == 48


def test_precompute_k_values_cover_business_range():
    # 19 个 K 覆盖 2h(cycles1.0..2.0) 与 4h 折算出的所有 K
    got = set()
    for tenths in range(10, 21):
        cyc = Decimal(tenths) / 10
        got.add(k_from_inputs(Decimal(400), Decimal(200), cyc))   # 2h
        got.add(k_from_inputs(Decimal(800), Decimal(200), cyc))   # 4h
    assert got == set(PRECOMPUTE_K_VALUES)


def test_day_optimal_by_k_sum_equals_yearly_average():
    """核心不变量：按 K 存每日和、再按窗口求和/加权 == 直接 yearly_average_prices。

    这是整个预计算正确性的基石——预计算存的每日 (sum,count) 聚合后必须和实时算一致。
    """
    days = {"d1": _day_cheap_then_dear(), "d2": _day_cheap_then_dear()}
    # 取一个真实业务 K：容量400/功率200/cycles1 → K=8
    cap, pwr, cyc = Decimal(400), Decimal(200), Decimal("1")
    k = k_from_inputs(cap, pwr, cyc)

    # 预计算路径：逐日 day_optimal_by_k[k] 求和
    c_sum = Decimal(0); d_sum = Decimal(0); slots = 0
    for prices in days.values():
        cs, ds, sc = day_optimal_by_k(prices, k_values=[k], min_action_minutes=30, switch_gap_minutes=15)[k]
        c_sum += cs; d_sum += ds; slots += sc
    pre_avg_c = c_sum / slots
    pre_avg_d = d_sum / slots

    # 实时路径
    cfg = _cfg(cap="400", power="200", cycles="1", min_action=30, gap=15)
    rt_avg_c, rt_avg_d = yearly_average_prices(days, cfg)

    assert pre_avg_c == rt_avg_c
    assert pre_avg_d == rt_avg_d


@pytest.mark.parametrize("seed", range(5))
def test_day_optimal_by_k_matches_independent_dp_for_all_business_k(seed):
    """共享最大 K 状态树提取出的每个 K 必须与独立 DP 完全一致。"""
    randomizer = random.Random(seed)
    prices = [Decimal(randomizer.randint(-100, 300)) / 10 for _ in range(96)]
    actual = day_optimal_by_k(prices)
    expected = {}
    for k in PRECOMPUTE_K_VALUES:
        actions = spot_pricing._optimize_day_core(prices, k, min_run=2, gap=1)
        charge_sum = Decimal(0)
        discharge_sum = Decimal(0)
        slots = 0
        for price, action in zip(prices, actions):
            if action == CHARGE:
                charge_sum += price
                slots += 1
            elif action == DISCHARGE:
                discharge_sum += price
        expected[k] = (charge_sum, discharge_sum, slots)
    assert actual == expected


def test_day_optimal_by_k_incomplete_day_returns_empty():
    assert day_optimal_by_k([Decimal(1)] * 50) == {}
