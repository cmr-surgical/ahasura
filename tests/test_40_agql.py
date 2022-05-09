import pytest
from pytest_mock import MockerFixture

from ahasura import ADMIN, Hasura, HasuraError

pytestmark = pytest.mark.anyio


async def test_agql_returns_ok(hasura: Hasura, mocker: MockerFixture) -> None:
    asyncClient = mocker.patch("httpx.AsyncClient").return_value
    asyncClient.__aenter__ = mocker.AsyncMock()
    post = asyncClient.__aenter__.return_value.post
    post.return_value.json = mocker.Mock(return_value={"data": {"item": [{"id": "X"}]}})

    ahasura = hasura.agql

    data = await ahasura(
        "query($name: String!) {...}",
        auth="Bearer REDACTED",
        headers={"x-hasura-something": "special"},
        name="value",
    )

    assert data == {"item": [{"id": "X"}]}

    post.assert_awaited_once_with(
        "http://localhost:8080/v1/graphql",
        headers={"authorization": "Bearer REDACTED", "x-hasura-something": "special"},
        json={"query": "query($name: String!) {...}", "variables": {"name": "value"}},
        timeout=10,
    )


async def test_agql_raises_HasuraError(hasura: Hasura, mocker: MockerFixture) -> None:
    asyncClient = mocker.patch("httpx.AsyncClient").return_value
    asyncClient.__aenter__ = mocker.AsyncMock()
    post = asyncClient.__aenter__.return_value.post
    post.return_value.json = mocker.Mock(return_value={"errors": "fake errors"})

    ahasura = hasura.agql

    with pytest.raises(HasuraError) as error:
        await ahasura("bad query", auth=ADMIN)

    assert error.value.response == {"errors": "fake errors"}

    post.assert_awaited_once_with(
        "http://localhost:8080/v1/graphql",
        headers={"x-hasura-admin-secret": "fake secret"},
        json={"query": "bad query", "variables": {}},
        timeout=10,
    )
