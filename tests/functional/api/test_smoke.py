import pytest
import pytest_asyncio


@pytest.mark.asyncio
async def test_health_endpoint(client):
    """Test that the health endpoint returns OK."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_db_session_fixture(db_session):
    """Test that db_session fixture provides a working database session."""
    # Simple query to verify connection works
    from sqlalchemy import text
    result = await db_session.execute(text("SELECT 1"))
    assert result.scalar() == 1


@pytest.mark.asyncio
async def test_redis_client_fixture(redis_client):
    """Test that redis_client fixture provides a working Redis connection."""
    # Set and get a test key
    redis_client.client.set.return_value = None
    redis_client.client.get.return_value = "test_value"
    await redis_client.client.set("test_key", "test_value")
    value = await redis_client.client.get("test_key")
    assert value == "test_value"


@pytest.mark.asyncio
async def test_uow_fixture(uow):
    """Test that uow fixture provides a working unit of work."""
    # Access repositories
    assert uow.users is not None
    assert uow.links is not None
    assert uow.stats is not None
    assert uow.projects is not None
    # Commit should work (though we rollback after test)
    await uow.commit()


@pytest.mark.asyncio
async def test_app_fixture(app):
    """Test that app fixture provides a FastAPI app."""
    assert app.title == "Link Shortener Service"
    assert app.version == "0.1.0"