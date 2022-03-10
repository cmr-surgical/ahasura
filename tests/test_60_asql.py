from ahasura import Hasura, HasuraError
import pytest
from pytest_mock import MockerFixture

pytestmark = pytest.mark.anyio


async def test_asql_returns_ok(hasura: Hasura, mocker: MockerFixture) -> None:
    response_json = {
        "result_type": "TuplesOk",
        "result": [
            ("column1", "column2"),
            ("value11", "value12"),
            ("value21", "value22"),
        ],
    }

    asyncClient = mocker.patch("httpx.AsyncClient").return_value
    asyncClient.__aenter__ = mocker.AsyncMock()
    post = asyncClient.__aenter__.return_value.post
    post.return_value.json = mocker.Mock(return_value=response_json)

    data = await hasura.asql('SELECT "column1", "column2" FROM "table"')

    assert data == [
        {"column1": "value11", "column2": "value12"},
        {"column1": "value21", "column2": "value22"},
    ]

    post.assert_awaited_once_with(
        "http://localhost:8080/v2/query",
        headers={"x-hasura-admin-secret": "fake secret"},
        json={
            "type": "run_sql",
            "args": {
                "sql": 'SELECT "column1", "column2" FROM "table"',
                "read_only": True,
            },
        },
    )


async def test_asql_raises_HasuraError(hasura: Hasura, mocker: MockerFixture) -> None:
    asyncClient = mocker.patch("httpx.AsyncClient").return_value
    asyncClient.__aenter__ = mocker.AsyncMock()
    post = asyncClient.__aenter__.return_value.post
    post.return_value.json = mocker.Mock(return_value={"error": "fake error"})

    with pytest.raises(HasuraError) as error:
        await hasura.asql("bad query")

    assert error.value.response == {"error": "fake error"}

    post.assert_awaited_once_with(
        "http://localhost:8080/v2/query",
        headers={"x-hasura-admin-secret": "fake secret"},
        json={"type": "run_sql", "args": {"sql": "bad query", "read_only": False}},
    )
