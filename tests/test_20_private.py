import pytest

from ahasura import ADMIN, Hasura, HasuraError

#
# _get_headers
#


def test_get_headers_for_admin(hasura: Hasura) -> None:
    assert hasura._get_headers(ADMIN) == {"x-hasura-admin-secret": "fake secret"}


def test_get_headers_for_non_admin(hasura: Hasura) -> None:
    assert hasura._get_headers("Bearer REDACTED") == {
        "authorization": "Bearer REDACTED"
    }


def test_get_headers_for_admin_with_custom_headers(hasura: Hasura) -> None:
    assert hasura._get_headers(ADMIN, {"x-hasura-something": "special"}) == {
        "x-hasura-admin-secret": "fake secret",
        "x-hasura-something": "special",
    }


def test_get_headers_for_non_admin_with_custom_headers(hasura: Hasura) -> None:
    assert hasura._get_headers(
        "Bearer REDACTED",
        headers={"x-hasura-something": "special"},
    ) == {
        "authorization": "Bearer REDACTED",
        "x-hasura-something": "special",
    }


#
# _get_run_sql_content
#


def test_get_run_sql_content_for_select(hasura: Hasura) -> None:
    query = """
        SeLeCt NULL;
    """

    assert hasura._get_run_sql_content(query) == {
        "type": "run_sql",
        "args": {"sql": query, "read_only": True},
    }


def test_get_run_sql_content_for_non_select(hasura: Hasura) -> None:
    query = """
        InSeRt INTO "fake_table" ("fake_column") VALUES ("fake_value");
    """

    assert hasura._get_run_sql_content(query) == {
        "type": "run_sql",
        "args": {"sql": query, "read_only": False},
    }


#
# _get_data
#


def test_get_data_raises_HasuraError(hasura: Hasura) -> None:
    with pytest.raises(HasuraError) as error:
        hasura._get_data({"errors": "fake errors"})

    assert error.value.response == {"errors": "fake errors"}


def test_get_data_returns_ok_data(hasura: Hasura) -> None:
    data = {"item": [{"id": "fake id"}]}
    assert hasura._get_data({"data": data}) == data


#
# _get_rows
#


def test_get_rows_raises_HasuraError(hasura: Hasura) -> None:
    with pytest.raises(HasuraError) as error:
        hasura._get_rows({"error": "fake error"})

    assert error.value.response == {"error": "fake error"}


def test_get_rows_returns_ok_for_CommandOk(hasura: Hasura) -> None:
    assert hasura._get_rows({"result_type": "CommandOk"}) == [{"ok": True}]


def test_get_rows_returns_ok_dicts_for_TuplesOk(hasura: Hasura) -> None:
    response_json = {
        "result_type": "TuplesOk",
        "result": [
            ("column1", "column2"),
            ("value11", "value12"),
            ("value21", "value22"),
        ],
    }

    expected_rows = [
        {"column1": "value11", "column2": "value12"},
        {"column1": "value21", "column2": "value22"},
    ]

    assert hasura._get_rows(response_json) == expected_rows
