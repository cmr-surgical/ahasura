import pytest
from pytest_mock import MockerFixture

from ahasura import ADMIN, Hasura, HasuraError


def test_gql_returns_ok(hasura: Hasura, mocker: MockerFixture) -> None:
    post = mocker.patch("httpx.post")
    post.return_value.json.return_value = {"data": {"item": [{"id": "fake"}]}}

    assert hasura.gql("query { item { id }}", auth=ADMIN) == {"item": [{"id": "fake"}]}

    post.assert_called_once_with(
        "http://localhost:8080/v1/graphql",
        headers={"x-hasura-admin-secret": "fake secret"},
        json={"query": "query { item { id }}", "variables": {}},
        timeout=10,
    )


def test_gql_shortcut_and_auth_and_vars(hasura: Hasura, mocker: MockerFixture) -> None:
    post = mocker.patch("httpx.post")
    post.return_value.json.return_value = {"data": {"item": [{"id": "fake"}]}}

    data = hasura(
        "query($name: String!) {...}",
        auth="Bearer REDACTED",
        name="value",
    )

    assert data == {"item": [{"id": "fake"}]}

    post.assert_called_once_with(
        "http://localhost:8080/v1/graphql",
        headers={"authorization": "Bearer REDACTED"},
        json={"query": "query($name: String!) {...}", "variables": {"name": "value"}},
        timeout=10,
    )


def test_gql_raises_HasuraError(hasura: Hasura, mocker: MockerFixture) -> None:
    post = mocker.patch("httpx.post")
    post.return_value.json.return_value = {"errors": "fake errors"}

    with pytest.raises(HasuraError) as error:
        hasura("bad query", auth=ADMIN)

    assert error.value.response == {"errors": "fake errors"}

    post.assert_called_once_with(
        "http://localhost:8080/v1/graphql",
        headers={"x-hasura-admin-secret": "fake secret"},
        json={"query": "bad query", "variables": {}},
        timeout=10,
    )
