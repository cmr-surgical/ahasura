import pytest
from pytest_mock import MockerFixture

from ahasura import Hasura, HasuraError


def test_sql_returns_ok(hasura: Hasura, mocker: MockerFixture) -> None:
    post = mocker.patch("httpx.post")
    post.return_value.json.return_value = {
        "result_type": "TuplesOk",
        "result": [
            ("column1", "column2"),
            ("value11", "value12"),
            ("value21", "value22"),
        ],
    }

    data = hasura.sql(
        'SELECT "column1", "column2" FROM "table"',
        headers={"x-hasura-something": "special"},
    )

    assert data == [
        {"column1": "value11", "column2": "value12"},
        {"column1": "value21", "column2": "value22"},
    ]

    post.assert_called_once_with(
        "http://localhost:8080/v2/query",
        headers={
            "x-hasura-admin-secret": "fake secret",
            "x-hasura-something": "special",
        },
        json={
            "type": "run_sql",
            "args": {
                "sql": 'SELECT "column1", "column2" FROM "table"',
                "read_only": True,
            },
        },
        timeout=10,
    )


def test_sql_raises_HasuraError(hasura: Hasura, mocker: MockerFixture) -> None:
    post = mocker.patch("httpx.post")
    post.return_value.json.return_value = {"error": "fake error"}

    with pytest.raises(HasuraError) as error:
        hasura.sql("bad query")

    assert error.value.response == {"error": "fake error"}

    post.assert_called_once_with(
        "http://localhost:8080/v2/query",
        headers={"x-hasura-admin-secret": "fake secret"},
        json={"type": "run_sql", "args": {"sql": "bad query", "read_only": False}},
        timeout=10,
    )
