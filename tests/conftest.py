from ahasura import Hasura
import pytest


@pytest.fixture(scope="session")
def hasura() -> Hasura:
    return Hasura("http://localhost:8080", admin_secret="fake secret")


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"
