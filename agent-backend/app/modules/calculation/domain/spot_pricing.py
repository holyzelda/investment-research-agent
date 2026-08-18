"""calculation 领域 · 现货电价多循环充放优化（逐日 DP + 年度加权）。纯计算，无 I/O。

依据《多循环储能充放电价格优化算法方案》(specs 2026-07-10)：
- 逐个自然日用有限状态 DP 求"理想条件下最大总价差"的充/放电时段（96 个 15 分钟槽）；
- 年度汇总：把全年入选充/放电槽电价按实际电量加权，得 avg_charge_price / avg_discharge_price。
- 本层不含收益计算、充放效率、损耗、SOC 上界、单位换算（换算在基础设施适配层做）。

数据缺失策略（按业务确认，覆盖 spec §11 的"任一缺点即整体失败"）：
- 只处理"恰好 96 点"的完整自然日；缺点/缺日/不满一年 → 跳过不计入，照常汇总；
- 全年无任何完整日或无正价差机会 → 返回 (None, None)。是否因"零数据"报错，由取数层决定。

约束（spec §8）：日初不能先放电；日终充放槽数相等（能量归零）；任意前缀放电≤充电；
每段连续充/放≥min_action；充放反向切换前须空闲≥switch_gap；等效循环上限 max_energy_slots。
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

# 槽动作
CHARGE = "C"
DISCHARGE = "D"
IDLE = "I"

SLOT_MINUTES = 15
SLOTS_PER_DAY = 96
_SLOT_HOURS = Decimal(SLOT_MINUTES) / Decimal(60)   # 0.25


@dataclass(frozen=True)
class SpotConfig:
    """优化输入（不含数据源信息）。"""
    capacity_mwh: Decimal
    rated_power_mw: Decimal
    max_equivalent_cycles: Decimal          # = 日均充放次数 daily_cycles
    min_action_minutes: int = 30            # 每段连续充/放最短时长
    switch_gap_minutes: int = 15            # 反向切换所需空闲时长

    def __post_init__(self) -> None:
        if self.capacity_mwh <= 0:
            raise ValueError("capacity_mwh 必须为正")
        if self.rated_power_mw <= 0:
            raise ValueError("rated_power_mw 必须为正")
        if self.max_equivalent_cycles < 0:
            raise ValueError("max_equivalent_cycles 不能为负")
        if self.min_action_minutes <= 0 or self.min_action_minutes % SLOT_MINUTES != 0:
            raise ValueError("min_action_minutes 必须为正且是 15 的整数倍")
        if self.switch_gap_minutes < 0 or self.switch_gap_minutes % SLOT_MINUTES != 0:
            raise ValueError("switch_gap_minutes 必须非负且是 15 的整数倍")


def _slot_energy(cfg: SpotConfig) -> Decimal:
    return cfg.rated_power_mw * _SLOT_HOURS


def _max_energy_slots(cfg: SpotConfig, t: int) -> int:
    """每日任一方向可用槽数上限 = min(floor(循环上限对应槽数), floor(T/2))。"""
    by_cycles = math.floor(cfg.max_equivalent_cycles * cfg.capacity_mwh / _slot_energy(cfg))
    return max(0, min(by_cycles, t // 2))


def _min_run_slots(cfg: SpotConfig) -> int:
    return cfg.min_action_minutes // SLOT_MINUTES


def _switch_gap_slots(cfg: SpotConfig) -> int:
    return cfg.switch_gap_minutes // SLOT_MINUTES


# ---- 有限状态机 ----
# fsm = (kind, length)
#   ('NONE', 0)                无动作
#   ('C', r) / ('D', r)        连续充/放，r 为连续槽数（封顶 min_run）
#   ('IAC', g) / ('IAD', g)    充后空闲 / 放后空闲，g 为空闲槽数（封顶 switch_gap）
_NONE = ("NONE", 0)


def _transition(state, action, K, min_run, gap):
    """返回 (ncc, ndc, nfsm, seg_delta) 或 None（非法）。seg_delta：新起一段充/放记 1。"""
    cc, dc, (kind, length) = state

    if action == IDLE:
        if kind == "NONE":
            return cc, dc, _NONE, 0
        if kind == "C":
            if length < min_run:
                return None            # 充电段未达最短时长，不能中断
            return cc, dc, ("IAC", min(1, gap)), 0
        if kind == "D":
            if length < min_run:
                return None
            return cc, dc, ("IAD", min(1, gap)), 0
        if kind == "IAC":
            return cc, dc, ("IAC", min(length + 1, gap)), 0
        if kind == "IAD":
            return cc, dc, ("IAD", min(length + 1, gap)), 0

    if action == CHARGE:
        if cc + 1 > K:
            return None
        if kind == "NONE":
            return cc + 1, dc, ("C", 1), 1
        if kind == "C":
            return cc + 1, dc, ("C", min(length + 1, min_run)), 0
        if kind == "IAC":                       # 同向续充（隔空闲后重开一段）
            return cc + 1, dc, ("C", 1), 1
        if kind == "D":                         # 放→充：仅当 gap==0 且放电段已达最短
            if gap == 0 and length >= min_run:
                return cc + 1, dc, ("C", 1), 1
            return None
        if kind == "IAD":                       # 放→空闲→充：须空闲达切换间隔
            if length >= gap:
                return cc + 1, dc, ("C", 1), 1
            return None

    if action == DISCHARGE:
        if dc + 1 > cc or dc + 1 > K:           # 能量：累计放≤累计充；且不超上限
            return None
        if kind == "NONE":
            return None                          # 空仓不能先放
        if kind == "D":
            return cc, dc + 1, ("D", min(length + 1, min_run)), 0
        if kind == "IAD":                       # 同向续放
            return cc, dc + 1, ("D", 1), 1
        if kind == "C":                         # 充→放：仅当 gap==0 且充电段已达最短
            if gap == 0 and length >= min_run:
                return cc, dc + 1, ("D", 1), 1
            return None
        if kind == "IAC":                       # 充→空闲→放：须空闲达切换间隔
            if length >= gap:
                return cc, dc + 1, ("D", 1), 1
            return None

    return None


def _terminal_ok(fsm, min_run) -> bool:
    """日终合法：充放相等（外部已判）；若末槽仍在充/放，该段须已达最短时长。"""
    kind, length = fsm
    if kind in ("NONE", "IAC", "IAD"):
        return True
    return length >= min_run


def optimize_day(prices, cfg: SpotConfig) -> list:
    """对一天（len=T，通常 96）价格求最优动作序列，返回长度 T 的 [C/D/I]。

    目标：max score = Σ p·d − Σ p·c。同分时按 (更少槽数, 更少动作段) 确定性打破平局，
    保证平价/无正价差时选零动作。
    """
    t_total = len(prices)
    K = _max_energy_slots(cfg, t_total)
    min_run = _min_run_slots(cfg)
    gap = _switch_gap_slots(cfg)
    return _optimize_day_core(prices, K, min_run, gap)


def _optimize_day_core(prices, K: int, min_run: int, gap: int) -> list:
    """DP 核心：直接以 (K, min_run, gap) 驱动，返回长度 T 的动作串。

    与 SpotConfig 解耦，便于预计算按 K 直接遍历（capacity/power 只经 K 影响结果，见 spec §7）。
    """
    t_total = len(prices)
    if K <= 0:
        return [IDLE] * t_total

    # state=(cc,dc,fsm) -> record=(score, segments)；同态取 (score 更大, segments 更少)
    current = {(0, 0, _NONE): (Decimal(0), 0)}
    parents: list = []
    for i in range(t_total):
        p = prices[i]
        nxt: dict = {}
        par: dict = {}
        for state, (score, segs) in current.items():
            for action in (IDLE, CHARGE, DISCHARGE):
                res = _transition(state, action, K, min_run, gap)
                if res is None:
                    continue
                ncc, ndc, nfsm, seg_delta = res
                if action == CHARGE:
                    nscore = score - p
                elif action == DISCHARGE:
                    nscore = score + p
                else:
                    nscore = score
                nstate = (ncc, ndc, nfsm)
                cand = (nscore, segs + seg_delta)
                cur = nxt.get(nstate)
                if cur is None or cand[0] > cur[0] or (cand[0] == cur[0] and cand[1] < cur[1]):
                    nxt[nstate] = cand
                    par[nstate] = (state, action)
        parents.append(par)
        current = nxt

    best_state = None
    best_key = None
    for state, (score, segs) in current.items():
        cc, dc, fsm = state
        if cc != dc or not _terminal_ok(fsm, min_run):
            continue
        key = (score, -cc, -segs)          # 最大分 → 最少槽 → 最少段
        if best_key is None or key > best_key:
            best_key = key
            best_state = state

    actions = [IDLE] * t_total
    state = best_state
    for i in range(t_total - 1, -1, -1):
        prev, action = parents[i][state]
        actions[i] = action
        state = prev
    return actions


def yearly_average_prices(
    daily_prices: dict, cfg: SpotConfig
) -> tuple[Optional[Decimal], Optional[Decimal]]:
    """把每一完整自然日的最优动作按实际电量加权，得年度 (avg_charge, avg_discharge)。

    daily_prices: {day_key: [price×96]}。非 96 点的日直接跳过。
    无入选槽（无完整日/无正价差）→ (None, None)。单位与入参电价一致（换算在适配层）。
    实时算法用；预计算走 day_optimal_by_k（按 K 存每日和，查询时按窗口求和）。
    """
    charge_sum = Decimal(0)
    discharge_sum = Decimal(0)
    charge_slots = 0
    discharge_slots = 0
    for _day, prices in daily_prices.items():
        if len(prices) != SLOTS_PER_DAY:
            continue
        for price, action in zip(prices, optimize_day(prices, cfg)):
            if action == CHARGE:
                charge_sum += price
                charge_slots += 1
            elif action == DISCHARGE:
                discharge_sum += price
                discharge_slots += 1
    if charge_slots == 0:
        return None, None
    return charge_sum / charge_slots, discharge_sum / discharge_slots


# ---- 预计算：按 K 逐日求和 ----

# 业务约束(cycles∈[1,2]步0.1，时长∈{2h,4h})下 K 的全部取值。见离线预计算讨论。
PRECOMPUTE_K_VALUES = [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 19, 20, 22, 24, 25, 27, 28, 30, 32]


def k_from_inputs(
    capacity_mwh: Decimal, rated_power_mw: Decimal, cycles: Decimal, t: int = SLOTS_PER_DAY
) -> int:
    """容量/功率/循环 → 每日单方向可用槽数上限 K = min(floor(cycles×容量/槽电量), T/2)。

    与 SpotConfig 内部口径一致；预计算与查询都用它把用户输入折算成 K。
    """
    slot_energy = rated_power_mw * _SLOT_HOURS
    by_cycles = math.floor(cycles * capacity_mwh / slot_energy)
    return max(0, min(by_cycles, t // 2))


def day_optimal_by_k(
    prices, k_values=PRECOMPUTE_K_VALUES, min_action_minutes: int = 30, switch_gap_minutes: int = 15
) -> dict:
    """对一天价格按多个 K 求最优，返回 {k: (charge_sum, discharge_sum, slot_count)}。

    预计算的原子单位：一天 × 各 K。charge/discharge_sum 为入选槽电价之和（原始，不乘系数）。
    一次按最大 K 推进状态，再从同一棵状态树提取各个 K，避免对同一天重复执行状态转移。
    非 96 点的日返回空 dict（调用方跳过）。
    """
    if len(prices) != SLOTS_PER_DAY:
        return {}
    requested = list(dict.fromkeys(k_values))
    if not requested:
        return {}
    min_run = min_action_minutes // SLOT_MINUTES
    gap = switch_gap_minutes // SLOT_MINUTES
    max_k = max(requested)

    # 所有较小 K 的可行路径都包含在 max_k 的状态树中；保留完整父指针，
    # 以便对每个 K 独立选择终态并回溯，保持原有的收益和并列规则。
    current = {(0, 0, _NONE): (Decimal(0), 0)}
    parents: list = []
    for price in prices:
        nxt: dict = {}
        par: dict = {}
        for state, (score, segs) in current.items():
            for action in (IDLE, CHARGE, DISCHARGE):
                res = _transition(state, action, max_k, min_run, gap)
                if res is None:
                    continue
                ncc, ndc, nfsm, seg_delta = res
                if action == CHARGE:
                    nscore = score - price
                elif action == DISCHARGE:
                    nscore = score + price
                else:
                    nscore = score
                nstate = (ncc, ndc, nfsm)
                cand = (nscore, segs + seg_delta)
                cur = nxt.get(nstate)
                if cur is None or cand[0] > cur[0] or (cand[0] == cur[0] and cand[1] < cur[1]):
                    nxt[nstate] = cand
                    par[nstate] = (state, action)
        parents.append(par)
        current = nxt

    out: dict = {}
    for target_k in requested:
        best_state = None
        best_key = None
        for state, (score, segs) in current.items():
            cc, dc, fsm = state
            if cc != dc or cc > target_k or not _terminal_ok(fsm, min_run):
                continue
            key = (score, -cc, -segs)
            if best_key is None or key > best_key:
                best_key = key
                best_state = state

        if best_state is None:
            # 全 IDLE 状态始终存在；此分支仅用于防御异常参数。
            out[target_k] = (Decimal(0), Decimal(0), 0)
            continue

        actions = [IDLE] * len(prices)
        state = best_state
        for index in range(len(prices) - 1, -1, -1):
            previous, action = parents[index][state]
            actions[index] = action
            state = previous

        c_sum = Decimal(0)
        d_sum = Decimal(0)
        slots = 0
        for price, action in zip(prices, actions):
            if action == CHARGE:
                c_sum += price
                slots += 1
            elif action == DISCHARGE:
                d_sum += price
        out[target_k] = (c_sum, d_sum, slots)
    return out
