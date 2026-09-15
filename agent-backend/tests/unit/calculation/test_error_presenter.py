from app.modules.calculation.application.error_presenter import (
    public_calc_error_code,
    public_calc_error_message,
)


def test_unknown_platform_error_is_not_exposed():
    code = public_calc_error_code("feishu_95201", "飞书错误 95201：server error")
    message = public_calc_error_message("飞书错误 95201：server error", "feishu_95201")

    assert code == "calculation_unavailable"
    assert message == "测算服务暂时不可用，请稍后重试"
    assert "飞书" not in message
    assert "95201" not in message
    assert "server error" not in message.lower()


def test_business_validation_error_is_preserved():
    assert public_calc_error_message("项目运营期仅支持15年或20年", "validation") == "项目运营期仅支持15年或20年"
