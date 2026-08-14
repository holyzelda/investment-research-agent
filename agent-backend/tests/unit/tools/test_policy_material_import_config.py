import pytest

from tools.policy_materials.database_config import database_config_from_url


def test_database_config_from_url_parses_sqlalchemy_mysql_url():
    config = database_config_from_url(
        "mysql+aiomysql://example_user:example_password@database.example.invalid:3307/policy_db?charset=utf8mb4"
    )

    assert config["host"] == "db.example"
    assert config["port"] == 3307
    assert config["user"] == "policy_user"
    assert config["password"] == "p@ss"
    assert config["database"] == "policy_db"
    assert config["charset"] == "utf8mb4"


@pytest.mark.parametrize(
    ("database_url", "message"),
    [
        ("", "Settings.database.url 不能为空"),
        ("sqlite:///local.db", "必须是 MySQL"),
        ("mysql+aiomysql://policy_user:password@/policy_db", "host"),
        ("mysql+aiomysql://db.example/policy_db", "username, password"),
        ("mysql+aiomysql://example_user:example_password@database.example.invalid", "database"),
    ],
)
def test_database_config_from_url_rejects_invalid_config(database_url: str, message: str):
    with pytest.raises(RuntimeError, match=message):
        database_config_from_url(database_url)
