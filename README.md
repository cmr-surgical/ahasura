# ahasura

Async and sync [Hasura](https://hasura.io/) client.

## Install

ahasura is available on PyPi

```
pip install ahasura
# Or
poetry add ahasura
```

## Quick example

```
from ahasura import ADMIN, Hasura
hasura = Hasura("http://localhost:8080", admin_secret="fake secret")

data = hasura(
    """
    query($id: uuid!) {
        item_by_pk(id: $id) {
            name
        }
    }
    """,
    auth=ADMIN,
    id="00000000-0000-0000-0000-000000000001",
)

item = data["item_by_pk"]
assert item["name"] == "Some name"
```

## Create client

* `hasura = Hasura(...)`
* Args:
    * `endpoint: str` - `HASURA_GRAPHQL_ENDPOINT`, without trailing `/` or `/v1/graphql`
    * `admin_secret: Optional[str]` - `HASURA_GRAPHQL_ADMIN_SECRET`, required for `auth=ADMIN` only
* `hasura` client just keeps the configuration above, so you can reuse global client(s)
* Shortcuts:
    * `hasura(...)` is a shortcut for sync GraphQL client: `hasura.gql(...)`
    * You can define a shortcut for Async GraphQL client: `ahasura = hasura.agql`

## Execute GraphQL query

* With shortcuts:
    * Sync: `data = hasura(...)`
    * Async: `data = await ahasura(...)`
* Without shortcuts:
    * Sync: `data = hasura.gql(...)`
    * Async: `data = await hasura.agql(...)`
* Args:
    * `query: str` - GraphQL query, e.g. `query { item { id }}`
    * `auth: str` - Either `ADMIN` or value of `Authorization` header, e.g. `Bearer {JWT}`
    * `headers: Optional[Dict[str, str]]` - Custom headers, if any
    * `**variables` - Variables used in `query`, if any
* Returns: GraphQL response data, e.g. `{"item": [{"id": "..."}]}`
* Raises: `HasuraError` - If JSON response from Hasura contains `errors` key

## Execute SQL query

* Sync: `rows = hasura.sql(...)`
* Async: `rows = await hasura.asql(...)`
* Args:
    * `query: str` - SQL query, e.g. `SELECT "id" FROM "item"`
    * `headers: Optional[Dict[str, str]]` - Custom headers, if any
* Returns:
    * Rows selected by `SELECT` query, e.g. `[{"id": "..."}]`
    * Or `[{"ok": True}]` for non-`SELECT` query
* Raises: `HasuraError` - If JSON response from Hasura contains `error` key

## Auth

* SQL queries are [admin-only](https://hasura.io/docs/latest/graphql/core/api-reference/schema-api/run-sql.html#run-sql)
* GraphQL queries can use both admin and non-admin `auth`
* `auth=ADMIN` is not default, because:
    * `sudo` is not default
    * It's easy to forget to propagate `Authorization` header of the user to Hasura
    * Declarative Hasura permissions are better than checking permissions in Python
    * When we set Hasura permissions, we should test them for each role supported

## How to test

### `test_item.py`

```
from typing import Any, Dict

from ahasura import Hasura, HasuraError
import pytest


def test_reader_reads_item_ok(
    hasura: Hasura,
    reader_auth: str,
    ok_item: Dict[str, Any],
) -> None:
    data = hasura(
        """
        query($id: uuid!) {
            item_by_pk(id: $id) {
                name
            }
        }
        """,
        auth=reader_auth,
        id=ok_item["id"],
    )

    item = data["item_by_pk"]
    assert item["name"] == "Some name"


def test_error(hasura: Hasura, reader_auth: str) -> None:
    with pytest.raises(HasuraError) as error:
        hasura("bad query", auth=reader_auth)

    assert error.value.response == {"errors": [...]}
```

### `conftest.py`

```
from typing import Any, Dict, Generator, List

from ahasura import ADMIN, Hasura
import jwt
import pytest

_TABLE_NAMES = ["item"]


@pytest.fixture(scope="session")
def hasura() -> Hasura:
    return Hasura("http://localhost:8080", admin_secret="fake secret")


@pytest.fixture(scope="session")
def reader_auth() -> str:
    decoded_token = ...
    encoded_token = jwt.encode(decoded_token, "")
    return f"Bearer {encoded_token}"


@pytest.fixture(scope="session")
def test_row_ids() -> List[str]:
    """
    When a test function creates a row in any table,
    it should append this `row["id"]` to `test_row_ids`

    UUIDs are unique across all tables with enough probability
    """
    return []


@pytest.fixture(scope="function")
def ok_item(hasura: Hasura, test_row_ids: List[str]) -> Dict[str, Any]:
    data = hasura(
        """
        mutation($item: item_insert_input!) {
            insert_item_one(object: $item) {
                id
                name
            }
        }
        """,
        auth=ADMIN,
        name="Some name",
    )
    item: Dict[str, Any] = data["insert_item_one"]
    test_row_ids.append(item["id"])
    return item


@pytest.fixture(scope="function", autouse=True)
def cleanup(hasura: Hasura, test_row_ids: List[str]) -> Generator[None, None, None]:
    """
    When the test function ends,
    this autouse fixture deletes all test rows from all tables
    """
    yield

    if test_row_ids:
        for table_name in _TABLE_NAMES:
            hasura(
                """
                mutation($ids: [uuid!]!) {
                    delete_{table_name}(where: {id: {_in: $ids}}) {
                        affected_rows
                    }
                }
                """.replace(
                    "{table_name}", table_name
                ),
                auth=ADMIN,
                ids=test_row_ids,
            )
        test_row_ids.clear()
```
