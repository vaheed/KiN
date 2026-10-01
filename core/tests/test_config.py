from app.config import Settings


def test_defaults_are_valid() -> None:
    settings = Settings(env="test")
    assert settings.port == 8000
    assert settings.embedding_dimensions == 1536
    assert settings.redis_url.endswith("/0")


def test_pool_validation() -> None:
    settings = Settings(env="test", KIN_DB_POOL_MIN=2, KIN_DB_POOL_MAX=4)
    assert settings.db_pool_min == 2
    assert settings.db_pool_max == 4


def test_database_url_quotes_credentials():
    settings = Settings(
        env="test",
        KIN_DB_USER="kin@svc",
        KIN_DB_PASSWORD="p@ss:word",
        KIN_DB_NAME="kin db",
    )
    assert settings.database_url == "postgresql://kin%40svc:p%40ss%3Aword@postgres:5432/kin%20db"
