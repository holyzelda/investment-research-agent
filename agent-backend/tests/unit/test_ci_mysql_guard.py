"""A DB integration run must never fall back to an existing configured server."""
import pytest

from tests.db.conftest import CI_MYSQL_URL, validated_ci_mysql_url


def _safe_environment(monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("IR_TEST_MYSQL_URL", CI_MYSQL_URL)
    monkeypatch.setenv("IR_DB_URL", CI_MYSQL_URL)
    for name in (
        "NACOS_ENABLED",
        "IR_FEISHU_ENABLED",
        "IR_SPOT_ENABLED",
        "IR_SPOT_DAILY_UPDATE_ENABLED",
    ):
        monkeypatch.setenv(name, "false")


def test_ci_mysql_guard_accepts_only_disposable_service(monkeypatch):
    _safe_environment(monkeypatch)
    assert validated_ci_mysql_url() == CI_MYSQL_URL


@pytest.mark.parametrize("variable,value", [
    ("GITHUB_ACTIONS", "false"),
    ("IR_TEST_MYSQL_URL", "mysql+aiomysql://ci_runner:x@internal.example/ir_agent"),
    ("IR_DB_URL", "sqlite+aiosqlite:///:memory:"),
    ("IR_FEISHU_ENABLED", "true"),
])
def test_ci_mysql_guard_rejects_unsafe_environment(monkeypatch, variable, value):
    _safe_environment(monkeypatch)
    monkeypatch.setenv(variable, value)
    with pytest.raises(RuntimeError):
        validated_ci_mysql_url()
