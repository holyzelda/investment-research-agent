from app.core.config.settings import FeishuConfig


def test_feishu_config_exposes_two_operation_year_template_tokens():
    cfg = FeishuConfig(
        template_token_15_years="template-15",
        template_token_20_years="template-20",
    )

    assert cfg.template_token_15_years == "template-15"
    assert cfg.template_token_20_years == "template-20"
