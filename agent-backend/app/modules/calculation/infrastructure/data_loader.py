"""calculation 基础设施 · 数据文件加载工具。"""
import json
import os
from functools import lru_cache

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def load_json(filename: str) -> dict:
    path = os.path.join(DATA_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@lru_cache
def _cached(filename: str) -> dict:
    return load_json(filename)


def param_dict_raw() -> dict:
    return _cached("param_dict.json")


def revenue_structure_raw() -> dict:
    return _cached("revenue_structure.json")


def mid_long_const_raw() -> dict:
    return _cached("mid_long_price_const.json")
