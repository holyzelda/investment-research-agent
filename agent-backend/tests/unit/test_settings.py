import os

from app.core.config import settings as settings_module
from app.core.config.settings import (
    FeishuConfig,
    get_app_config,
    get_cors_config,
    get_nacos_config,
    get_settings,
    reload_settings,
)


def test_feishu_config_exposes_two_operation_year_template_tokens():
    cfg = FeishuConfig(
        template_token_15_years="template-15",
        template_token_20_years="template-20",
    )

    assert cfg.template_token_15_years == "template-15"
    assert cfg.template_token_20_years == "template-20"


def test_run_env_file_loads_startup_settings(monkeypatch, tmp_path):
    env_file = tmp_path / "bootstrap.env"
    env_file.write_text(
        "APP_PORT=19089\n"
        "NACOS_ENABLED=false\n"
        "IR_DB_URL=sqlite+aiosqlite:///env-file.db\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("APP_PORT", raising=False)
    monkeypatch.delenv("NACOS_ENABLED", raising=False)
    monkeypatch.delenv("IR_DB_URL", raising=False)
    monkeypatch.setenv("ENV_FILE", str(env_file))

    try:
        import importlib
        import sys

        sys.modules.pop("run", None)
        sys.modules.pop("app.main", None)
        importlib.import_module("run")
        settings = reload_settings()

        assert settings.app.port == 19089
        assert settings.nacos.enabled is False
        assert settings.database.url == "sqlite+aiosqlite:///env-file.db"
    finally:
        os.environ.pop("APP_PORT", None)
        os.environ.pop("NACOS_ENABLED", None)
        os.environ.pop("IR_DB_URL", None)
        sys.modules.pop("run", None)
        sys.modules.pop("app.main", None)
        get_settings.cache_clear()


def test_nacos_business_configuration_overrides_explicit_business_environment(monkeypatch):
    monkeypatch.setenv("IR_DB_URL", "sqlite+aiosqlite:///environment.db")
    settings_module.set_nacos_overrides({
        "database": {"url": "sqlite+aiosqlite:///nacos.db"},
    })

    settings = reload_settings()

    assert settings.database.url == "sqlite+aiosqlite:///nacos.db"
    settings_module.clear_nacos_overrides()
    get_settings.cache_clear()


def test_log_and_cors_are_loaded_from_env_and_ignore_nacos(monkeypatch):
    monkeypatch.setenv("APP_LOG_RETENTION", "14 days")
    monkeypatch.setenv("APP_CORS_ALLOW_ORIGINS", "https://a.example, https://b.example")
    monkeypatch.setenv("APP_CORS_ALLOW_CREDENTIALS", "false")
    settings_module.set_nacos_overrides({
        "log": {"retention": "1 day"},
        "cors": {"allow_origins": ["https://nacos.example"], "allow_credentials": True},
    })

    settings = reload_settings()

    assert settings.log.retention == "14 days"
    assert settings.cors.allow_origins == ["https://a.example", "https://b.example"]
    assert settings.cors.allow_credentials is False
    assert "log" not in settings_module._nacos_overrides
    assert "cors" not in settings_module._nacos_overrides

    settings_module.clear_nacos_overrides()
    get_settings.cache_clear()


def test_section_getters_share_the_current_settings_snapshot():
    settings = get_settings()

    assert get_app_config() is settings.app
    assert get_cors_config() is settings.cors
    assert get_nacos_config() is settings.nacos


def test_run_module_loads_env_file_before_creating_app(monkeypatch, tmp_path):
    env_file = tmp_path / "bootstrap.env"
    env_file.write_text(
        "APP_PORT=19089\n"
        "NACOS_ENABLED=false\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("APP_PORT", raising=False)
    monkeypatch.delenv("NACOS_ENABLED", raising=False)
    monkeypatch.setenv("ENV_FILE", str(env_file))

    import importlib
    import sys

    try:
        sys.modules.pop("run", None)
        sys.modules.pop("app.main", None)
        importlib.import_module("run")
        settings = reload_settings()

        assert settings.app.port == 19089
        assert settings.nacos.enabled is False
    finally:
        os.environ.pop("APP_PORT", None)
        os.environ.pop("NACOS_ENABLED", None)
        sys.modules.pop("run", None)
        sys.modules.pop("app.main", None)
        get_settings.cache_clear()
