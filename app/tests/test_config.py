import pytest

from crud_generator.config import DatabaseConfig


def test_database_config_valid() -> None:
    config = DatabaseConfig(
        host="localhost",
        port=5432,
        database="crud_test",
        user="postgres",
        password="secret",
    )

    assert config.host == "localhost"
    assert config.port == 5432
    assert config.database == "crud_test"
    assert config.user == "postgres"


def test_password_is_not_shown_in_repr() -> None:
    config = DatabaseConfig(
        host="localhost",
        port=5432,
        database="crud_test",
        user="postgres",
        password="super_secret_password",
    )

    assert "super_secret_password" not in repr(config)


def test_empty_host_is_rejected() -> None:
    with pytest.raises(ValueError):
        DatabaseConfig(
            host="",
            port=5432,
            database="crud_test",
            user="postgres",
            password="secret",
        )


def test_invalid_port_is_rejected() -> None:
    with pytest.raises(ValueError):
        DatabaseConfig(
            host="localhost",
            port=70000,
            database="crud_test",
            user="postgres",
            password="secret",
        )