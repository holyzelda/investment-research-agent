"""朱雀星核正式报告项目标题规则。"""
from app.modules.report.application.project_naming import (
    build_report_project_name,
    build_report_title,
    format_project_location,
    normalize_project_region,
)


def test_normalizes_administrative_regions_and_preserves_grid_regions():
    assert normalize_project_region("浙江") == "浙江省"
    assert normalize_project_region("上海") == "上海市"
    assert normalize_project_region("深圳") == "深圳市"
    assert normalize_project_region("新疆") == "新疆维吾尔自治区"
    assert normalize_project_region("广西") == "广西壮族自治区"
    assert normalize_project_region("宁夏") == "宁夏回族自治区"
    assert normalize_project_region("西藏") == "西藏自治区"
    assert normalize_project_region("冀北") == "冀北"
    assert normalize_project_region("河北南网") == "河北南网"
    assert normalize_project_region("蒙东") == "蒙东"
    assert normalize_project_region("蒙西") == "蒙西"
    assert normalize_project_region("冀南") == "冀南"
    assert normalize_project_region("未知地区") == "未知地区"


def test_removes_only_an_exact_region_prefix_from_node_name():
    assert format_project_location("浙江", "浙江嘉兴站") == "浙江省嘉兴站"
    assert format_project_location("浙江", "浙江省嘉兴站") == "浙江省嘉兴站"
    assert format_project_location("浙江", "浙北嘉兴站") == "浙江省浙北嘉兴站"
    assert format_project_location("浙江", "浙江") == "浙江省"
    assert format_project_location("冀北", "冀北承德站") == "冀北承德站"
    assert format_project_location("甘肃", None) == "甘肃省"


def test_builds_report_names_from_location_and_scale():
    assert build_report_title("浙江", "浙江嘉兴站", 200.0, 800.0) == (
        "浙江省嘉兴站200MW/800MWh储能项目报告"
    )
    assert build_report_project_name("浙江", "浙江嘉兴站", 200.0, 800.0) == (
        "浙江省嘉兴站200MW/800MWh独立储能项目"
    )
