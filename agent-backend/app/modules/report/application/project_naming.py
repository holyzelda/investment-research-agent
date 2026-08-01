"""朱雀星核项目标题的地区、节点与规模格式化规则。"""
from __future__ import annotations


_REGION_DISPLAY_NAMES = {
    "浙江": "浙江省",
    "上海": "上海市",
    "广东": "广东省",
    "江苏": "江苏省",
    "湖南": "湖南省",
    "深圳": "深圳市",
    "海南": "海南省",
    "重庆": "重庆市",
    "河南": "河南省",
    "安徽": "安徽省",
    "湖北": "湖北省",
    "天津": "天津市",
    "四川": "四川省",
    "陕西": "陕西省",
    "贵州": "贵州省",
    "辽宁": "辽宁省",
    "吉林": "吉林省",
    "山东": "山东省",
    "黑龙江": "黑龙江省",
    "山西": "山西省",
    "福建": "福建省",
    "江西": "江西省",
    "新疆": "新疆维吾尔自治区",
    "冀北": "冀北",
    "河北南网": "河北南网",
    "蒙东": "蒙东",
    "青海": "青海省",
    "云南": "云南省",
    "北京": "北京市",
    "广西": "广西壮族自治区",
    "宁夏": "宁夏回族自治区",
    "蒙西": "蒙西",
    "甘肃": "甘肃省",
    "西藏": "西藏自治区",
    "冀南": "冀南",
}


def normalize_project_region(region) -> str:
    value = str(region or "").strip()
    return _REGION_DISPLAY_NAMES.get(value, value)


def format_project_location(region, node_name) -> str:
    raw_region = str(region or "").strip()
    display_region = normalize_project_region(raw_region)
    display_node = str(node_name or "").strip()
    prefixes = sorted({display_region, raw_region} - {""}, key=len, reverse=True)
    repeated_prefix = next((prefix for prefix in prefixes if display_node.startswith(prefix)), None)
    if repeated_prefix:
        display_node = display_node[len(repeated_prefix):].lstrip()
    return f"{display_region}{display_node}"


def _number(value):
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def format_project_scale(power, capacity) -> str:
    return f"{_number(power)}MW/{_number(capacity)}MWh"


def build_report_title(region, node_name, power, capacity) -> str:
    return f"{format_project_location(region, node_name)}{format_project_scale(power, capacity)}储能项目报告"


def build_report_project_name(region, node_name, power, capacity) -> str:
    return f"{format_project_location(region, node_name)}{format_project_scale(power, capacity)}独立储能项目"
