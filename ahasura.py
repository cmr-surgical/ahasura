"""Async and sync Hasura client"""

__version__ = "1.1.0"

from typing import Any, Dict, List, Optional

import httpx

ADMIN = "ADMIN"


class Hasura:
    """Async and sync Hasura client"""

    graphql_endpoint: str
    sql_endpoint: str
    admin_secret: Optional[str] = None

    def __init__(self, endpoint: str, admin_secret: Optional[str] = None) -> None:
        """Create Hasura client

        It just keeps the configuration passed, so you can reuse global client(s)

        Args:
            endpoint: `HASURA_GRAPHQL_ENDPOINT`, without trailing `/` or `/v1/graphql`
            admin_secret: `HASURA_GRAPHQL_ADMIN_SECRET`, required for `auth=ADMIN` only

        Examples:
            Client::

                hasura = Hasura(...)

            `hasura(...)` is a shortcut for sync GraphQL client: `hasura.gql(...)`

            You can define a shortcut for Async GraphQL client::

                ahasura = hasura.agql
        """
        assert not endpoint.endswith("/")
        assert not endpoint.endswith("/v1/graphql")
        assert not endpoint.endswith("/v2/query")

        self.graphql_endpoint = f"{endpoint}/v1/graphql"
        self.sql_endpoint = f"{endpoint}/v2/query"
        self.admin_secret = admin_secret

    def gql(self, query: str, auth: str, **variables) -> Dict[str, Any]:
        """Execute GraphQL query at Hasura, sync version

        Args:
            query: GraphQL query, e.g. `query { item { id }}`
            auth: Either `ADMIN` or value of `Authorization` header, e.g. `Bearer {JWT}`
            **variables: Variables used in `query`, if any

        Returns:
            GraphQL response data, e.g. `{"item": [{"id": "..."}]}`

        Raises:
            HasuraError: If JSON response from Hasura contains `errors` key

        Examples:
            With shortcut::

                data = hasura(...)

            Without shortcut::

                data = hasura.gql(...)
        """

        headers = self._get_headers(auth)
        content = {"query": query, "variables": variables}
        response = httpx.post(self.graphql_endpoint, headers=headers, json=content)
        return self._get_data(response.json())

    __call__ = gql  # `hasura(...)` is a shortcut for `hasura.gql(...)`

    async def agql(self, query: str, auth: str, **variables) -> Dict[str, Any]:
        """Execute GraphQL query at Hasura, async version

        Please see the docs of sync version

        Examples:
            With shortcut::

                data = await ahasura(...)

            Without shortcut::

                data = await hasura.agql(...)
        """
        headers = self._get_headers(auth)
        content = {"query": query, "variables": variables}

        async with httpx.AsyncClient() as ahttpx:
            response = await ahttpx.post(
                self.graphql_endpoint, headers=headers, json=content
            )

        return self._get_data(response.json())

    def sql(self, query: str) -> List[Dict[str, Any]]:
        """Execute SQL query at Hasura, sync version

        Args:
            query: SQL query, e.g. `SELECT "id" FROM "item"`

        Returns:
            Rows selected by `SELECT` query, e.g. `[{"id": "..."}]`,
            or `[{"ok": True}]` for non-`SELECT` query

        Raises:
            HasuraError: If JSON response from Hasura contains `error` key

        Example::

            rows = hasura.sql(...)
        """
        headers = self._get_headers(ADMIN)
        content = self._get_run_sql_content(query)
        response = httpx.post(self.sql_endpoint, headers=headers, json=content)
        return self._get_rows(response.json())

    async def asql(self, query: str) -> List[Dict[str, Any]]:
        """Execute SQL query at Hasura, async version

        Please see the docs of sync version

        Example::

            rows = await hasura.asql(...)
        """
        headers = self._get_headers(ADMIN)
        content = self._get_run_sql_content(query)

        async with httpx.AsyncClient() as ahttpx:
            response = await ahttpx.post(
                self.sql_endpoint, headers=headers, json=content
            )

        return self._get_rows(response.json())

    # Private DRY implementation parts of the public API above:

    def _get_headers(self, auth: str) -> Dict[str, str]:
        if auth == ADMIN:
            assert self.admin_secret
            return {"x-hasura-admin-secret": self.admin_secret}

        return {"authorization": auth}

    def _get_run_sql_content(self, query: str) -> Dict[str, Any]:
        read_only = query.lstrip()[:6].upper() == "SELECT"
        return {"type": "run_sql", "args": {"sql": query, "read_only": read_only}}

    def _get_data(self, response_json: Dict[str, Any]) -> Dict[str, Any]:
        if "errors" in response_json:
            raise HasuraError(response_json)

        data = response_json["data"]
        assert isinstance(data, dict)
        return data

    def _get_rows(self, response_json: Dict[str, Any]) -> List[Dict[str, Any]]:
        if "error" in response_json:
            raise HasuraError(response_json)

        if response_json["result_type"] == "CommandOk":
            return [{"ok": True}]

        assert response_json["result_type"] == "TuplesOk", response_json
        result = response_json["result"]
        column_names = result[0]
        return [dict(zip(column_names, row)) for row in result[1:]]


class HasuraError(Exception):
    """Exception raised if JSON response from Hasura contains `errors` or `error` key

    Attributes:
        response - Parsed JSON response from Hasura

    Examples:
        Testing::

            def test_error() -> None:
                with pytest.raises(HasuraError) as error:
                    hasura("bad query", auth="bad auth")

                assert error.value.response == {"errors": [...]}
    """

    def __init__(self, response: Dict[str, Any]):
        self.response = response
        super().__init__(response)
