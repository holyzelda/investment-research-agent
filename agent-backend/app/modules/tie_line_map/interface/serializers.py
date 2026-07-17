"""tie_line_map 模块 · interface 序列化（domain → 前端 camelCase JSON）。

- 列表接口：线路数组 + 静态统计（stats）+ 筛选可选项（filters）。
- 详情接口：单条线路完整静态字段。

注意：原型图「功率趋势 / 最高·最低 MW / 时间范围」依赖时序功率数据，
底表 ir_tie_line_map 无此类字段，故此处不产出任何 MW 时序，
统计仅基于静态数据（线路数、覆盖区域、电压档、额定容量合计）。
"""
from __future__ import annotations

from app.modules.tie_line_map.domain.models import TieLine


def _line_to_dict(line: TieLine) -> dict:
    return {
        "id": line.id,
        "name": line.name,
        "startPoint": line.start_point,
        "endPoint": line.end_point,
        "startRegion": line.start_region,
        "endRegion": line.end_region,
        "startLng": line.start_longitude,
        "startLat": line.start_latitude,
        "endLng": line.end_longitude,
        "endLat": line.end_latitude,
        "lengthText": line.length_text,
        "voltageText": line.voltage_text,
        "ratedCapacityMw": line.rated_capacity_mw,
        "operationYear": line.operation_year,
    }


def _line_to_detail(line: TieLine) -> dict:
    """详情比列表多出坐标基准/数据基准/来源备注等溯源字段。"""
    detail = _line_to_dict(line)
    detail.update({
        "coordinateBasis": line.coordinate_basis,
        "dataBasisNote": line.data_basis_note,
        "sourceNote": line.source_note,
    })
    return detail


def _stats(lines: list[TieLine]) -> dict:
    regions = set()
    for line in lines:
        if line.start_region:
            regions.add(line.start_region)
        if line.end_region:
            regions.add(line.end_region)
    voltages = {line.voltage_text for line in lines if line.voltage_text}
    total_capacity = sum(line.rated_capacity_mw or 0 for line in lines)
    return {
        "lineCount": len(lines),
        "regionCount": len(regions),
        "voltageLevelCount": len(voltages),
        "totalCapacityMw": total_capacity,
    }


def _filters(lines: list[TieLine]) -> dict:
    voltages = sorted({line.voltage_text for line in lines if line.voltage_text})
    regions = sorted({
        region
        for line in lines
        for region in (line.start_region, line.end_region)
        if region
    })
    return {"voltageOptions": voltages, "regionOptions": regions}


def serialize_lines(lines: list[TieLine]) -> dict:
    return {
        "items": [_line_to_dict(line) for line in lines],
        "stats": _stats(lines),
        "filters": _filters(lines),
    }


def serialize_line_detail(line: TieLine) -> dict:
    return _line_to_detail(line)
