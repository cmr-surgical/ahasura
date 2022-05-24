import pytest

from ahasura import Hasura, __version__


def test_version() -> None:
    assert __version__ == "1.4.1"

    with open("pyproject.toml", "r") as pyproject:
        assert pyproject.readlines()[2] == f'version = "{__version__}"\n'


def test_create_client_requires_endpoint() -> None:
    with pytest.raises(TypeError) as error:
        Hasura()  # type: ignore

    assert "missing 1 required positional argument: 'endpoint'" in repr(error.value)


def test_create_client_requires_endpoint_only() -> None:
    Hasura("http://localhost:8080")


def test_create_client_stores_args():
    hasura = Hasura("http://localhost:8080", admin_secret="fake secret")
    assert hasura.graphql_endpoint == "http://localhost:8080/v1/graphql"
    assert hasura.sql_endpoint == "http://localhost:8080/v2/query"
    assert hasura.admin_secret == "fake secret"
