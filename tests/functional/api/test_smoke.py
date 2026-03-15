import pytest
import pytest_asyncio

#ваще что запустилось чекнем
@pytest.mark.asyncio
async def test_health_endpoint(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_db_session_fixture(db_session):
    from sqlalchemy import text
    result = await db_session.execute(text("SELECT 1"))
    assert result.scalar() == 1


@pytest.mark.asyncio
async def test_redis_client_fixture(redis_client):
    redis_client.client.set.return_value = None
    redis_client.client.get.return_value = "test_value"
    await redis_client.client.set("test_key", "test_value")
    value = await redis_client.client.get("test_key")
    assert value == "test_value"


@pytest.mark.asyncio
async def test_uow_fixture(uow):
    assert uow.users is not None
    assert uow.links is not None
    assert uow.stats is not None
    assert uow.projects is not None

    await uow.commit()


@pytest.mark.asyncio
async def test_app_fixture(app):
    assert app.title == "Link Shortener Service"
    assert app.version == "0.1.0"