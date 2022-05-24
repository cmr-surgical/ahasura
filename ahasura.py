"""Async and sync Hasura client"""

__version__ = "1.4.1"

from typing import Any, Dict, List, Optional

import httpx

ADMIN = "ADMIN"


class Hasura:
    """Async and sync Hasura client"""

    graphql_endpoint: str
    sql_endpoint: str
    admin_secret: Optional[str] = None
    timeout: float

    def __init__(
        self,
        endpoint: str,
        admin_secret: Optional[str] = None,
        timeout: float = 10,
    ) -> None:
        """Create Hasura client

        It just keeps the configuration passed, so you can reuse global client(s)

        Args:
            endpoint: `HASURA_GRAPHQL_ENDPOINT`, without trailing `/` or `/v1/graphql`
            admin_secret: `HASURA_GRAPHQL_ADMIN_SECRET`, required for `auth=ADMIN` only
            timeout: Seconds of network inactivity allowed. `None` disables the timeout

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
        self.timeout = timeout

    def gql(
        self,
        query: str,
        auth: str,
        headers: Optional[Dict[str, str]] = None,
        **variables,
    ) -> Dict[str, Any]:
        """Execute GraphQL query at Hasura, sync version

        Args:
            query: GraphQL query, e.g. `query { item { id }}`
            auth: Either `ADMIN` or value of `Authorization` header, e.g. `Bearer {JWT}`
            headers: Custom headers, if any
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
        response = httpx.post(
            self.graphql_endpoint,
            headers=self._get_headers(auth, headers),
            json={"query": query, "variables": variables},
            timeout=self.timeout,
        )

        return self._get_data(response.json())

    __call__ = gql  # `hasura(...)` is a shortcut for `hasura.gql(...)`

    async def agql(
        self,
        query: str,
        auth: str,
        headers: Optional[Dict[str, str]] = None,
        **variables,
    ) -> Dict[str, Any]:
        """Execute GraphQL query at Hasura, async version

        Please see the docs of sync version

        Examples:
            With shortcut::

                data = await ahasura(...)

            Without shortcut::

                data = await hasura.agql(...)
        """
        async with httpx.AsyncClient() as ahttpx:
            response = await ahttpx.post(
                self.graphql_endpoint,
                headers=self._get_headers(auth, headers),
                json={"query": query, "variables": variables},
                timeout=self.timeout,
            )

        return self._get_data(response.json())

    def sql(
        self,
        query: str,
        headers: Optional[Dict[str, str]] = None,
    ) -> List[Dict[str, Any]]:
        """Execute SQL query at Hasura, sync version

        Args:
            query: SQL query, e.g. `SELECT "id" FROM "item"`
            headers: Custom headers, if any

        Returns:
            Rows selected by `SELECT` query, e.g. `[{"id": "..."}]`,
            or `[{"ok": True}]` for non-`SELECT` query

        Raises:
            HasuraError: If JSON response from Hasura contains `error` key

        Example::

            rows = hasura.sql(...)
        """
        response = httpx.post(
            self.sql_endpoint,
            headers=self._get_headers(ADMIN, headers),
            json=self._get_run_sql_content(query),
            timeout=self.timeout,
        )

        return self._get_rows(response.json())

    async def asql(
        self,
        query: str,
        headers: Optional[Dict[str, str]] = None,
    ) -> List[Dict[str, Any]]:
        """Execute SQL query at Hasura, async version

        Please see the docs of sync version

        Example::

            rows = await hasura.asql(...)
        """
        async with httpx.AsyncClient() as ahttpx:
            response = await ahttpx.post(
                self.sql_endpoint,
                headers=self._get_headers(ADMIN, headers),
                json=self._get_run_sql_content(query),
                timeout=self.timeout,
            )

        return self._get_rows(response.json())

    # Private DRY implementation parts of the public API above:

    def _get_headers(
        self,
        auth: str,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        if auth == ADMIN:
            assert self.admin_secret
            result = {"x-hasura-admin-secret": self.admin_secret}
        else:
            result = {"authorization": auth}

        if headers:
            result.update(headers)
        return result

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
