import pytest
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, call
from uuid import uuid4


class TestCacheBehaviour:
    """Functional tests for cache behaviour."""

    @pytest.mark.asyncio
    async def test_redirect_cache_miss_db_fetch_cache_set(
        self, client, redis_client, uow, test_settings
    ):
        """Test redirect with cache miss: DB fetch occurs and cache is set."""
        # Arrange
        # Create a link via API
        payload = {
            "original_url": "https://example.com",
            "custom_alias": "cachetest"
        }
        response = await client.post("/links/shorten", json=payload)
        assert response.status_code == 201
        data = response.json()
        short_code = data["short_code"]
        original_url = data["original_url"]

        # Reset mock calls (redis client is mocked in conftest)
        redis_client.client.get.reset_mock()
        redis_client.client.setex.reset_mock()

        # Act: First redirect (cache miss)
        response = await client.get(f"/opupupa/{short_code}", follow_redirects=False)

        # Assert
        assert response.status_code == 307

        # Verify cache.get was called
        redis_client.client.get.assert_called_once_with(f"link:code:{short_code}")

        # Verify cache.set was called (cache miss -> set cache)
        # The cache.set is called with original_url, expires_at, link_id, ttl_sec
        # We need to check that setex was called with appropriate arguments
        assert redis_client.client.setex.call_count == 1
        setex_call = redis_client.client.setex.call_args
        assert setex_call[0][0] == f"link:code:{short_code}"
        # TTL should be DEFAULT_CACHE_TTL_SEC from settings
        assert setex_call[0][1] == test_settings.DEFAULT_CACHE_TTL_SEC
        # Parse JSON data to verify structure
        cached_data = json.loads(setex_call[0][2])
        assert cached_data["original_url"] == original_url
        # expires_at may be None or ISO string
        # link_id should be a valid UUID string
        assert "link_id" in cached_data

    @pytest.mark.asyncio
    async def test_redirect_cache_hit_no_cache_set(self, client, redis_client, uow):
        """Test redirect with cache hit: cache.set is not called."""
        # Arrange
        # Create a link via API
        payload = {
            "original_url": "https://example.com",
            "custom_alias": "cachehittest"
        }
        response = await client.post("/links/shorten", json=payload)
        assert response.status_code == 201
        data = response.json()
        short_code = data["short_code"]
        original_url = data["original_url"]

        # Reset mocks before first redirect to ignore cache.set from link creation
        redis_client.client.get.reset_mock()
        redis_client.client.setex.reset_mock()

        # First request to populate cache
        await client.get(f"/opupupa/{short_code}", follow_redirects=False)

        # Capture cached data from setex call
        assert redis_client.client.setex.call_count == 1
        setex_call = redis_client.client.setex.call_args
        cached_json = setex_call[0][2]  # JSON string
        # Set get to return cached data
        redis_client.client.get.return_value = cached_json

        # Reset mocks (keeps return_value)
        redis_client.client.get.reset_mock()
        redis_client.client.setex.reset_mock()

        # Act: Second redirect (cache hit)
        response = await client.get(f"/opupupa/{short_code}", follow_redirects=False)

        # Assert
        assert response.status_code == 307

        # Verify cache.get was called
        redis_client.client.get.assert_called_once_with(f"link:code:{short_code}")

        # Verify cache.set (setex) was NOT called because cached data exists
        redis_client.client.setex.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_invalidated_on_link_update(self, client, redis_client, uow):
        """Test cache invalidated when link is updated."""
        # Arrange
        # Create a link via API
        payload = {
            "original_url": "https://example.com",
            "custom_alias": "updatecachetest"
        }
        response = await client.post("/links/shorten", json=payload)
        assert response.status_code == 201
        short_code = response.json()["short_code"]

        # Populate cache by redirecting
        await client.get(f"/opupupa/{short_code}", follow_redirects=False)

        # Reset mocks
        redis_client.client.delete.reset_mock()

        # Act: Update link (change original URL)
        update_payload = {
            "original_url": "https://updated-example.com"
        }
        response = await client.put(f"/links/{short_code}", json=update_payload)
        assert response.status_code == 200

        # Assert: cache.invalidate was called (delete on redis)
        redis_client.client.delete.assert_called_once_with(f"link:code:{short_code}")

    @pytest.mark.asyncio
    async def test_cache_invalidated_on_link_update_with_new_short_code(
        self, client, redis_client, uow
    ):
        """Test cache invalidated for both old and new short codes when short_code changes."""
        # Arrange
        # Create a link via API
        payload = {
            "original_url": "https://example.com",
            "custom_alias": "updatealias"
        }
        response = await client.post("/links/shorten", json=payload)
        assert response.status_code == 201
        short_code = response.json()["short_code"]

        # Populate cache by redirecting
        await client.get(f"/opupupa/{short_code}", follow_redirects=False)

        # Reset mocks
        redis_client.client.delete.reset_mock()

        # Act: Update link with new short_code
        new_alias = "newalias"
        update_payload = {
            "new_short_code": new_alias
        }
        response = await client.put(f"/links/{short_code}", json=update_payload)
        assert response.status_code == 200

        # Assert: cache.invalidate called for old short_code and new short_code
        assert redis_client.client.delete.call_count == 2
        delete_calls = redis_client.client.delete.call_args_list
        delete_keys = [call[0][0] for call in delete_calls]
        assert f"link:code:{short_code}" in delete_keys
        assert f"link:code:{new_alias}" in delete_keys

    @pytest.mark.asyncio
    async def test_cache_invalidated_on_link_delete(self, client, redis_client, uow):
        """Test cache invalidated when link is deleted."""
        # Arrange
        # Create a link via API
        payload = {
            "original_url": "https://example.com",
            "custom_alias": "deletecachetest"
        }
        response = await client.post("/links/shorten", json=payload)
        assert response.status_code == 201
        short_code = response.json()["short_code"]

        # Populate cache by redirecting
        await client.get(f"/opupupa/{short_code}", follow_redirects=False)

        # Reset mocks
        redis_client.client.delete.reset_mock()

        # Act: Delete link
        response = await client.delete(f"/links/{short_code}")
        assert response.status_code == 204

        # Assert: cache.invalidate was called
        redis_client.client.delete.assert_called_once_with(f"link:code:{short_code}")

    @pytest.mark.asyncio
    async def test_cache_invalidated_after_purge_job(
        self, client, redis_client, uow, test_settings
    ):
        """Test cache invalidated when purge job marks links as expired."""
        # This test requires simulating expired links and running purge job.
        # Since purge job is mocked in tests (PurgeExpiredLinksJob.start),
        # we need to directly call the use case and verify cache invalidation.
        # Arrange
        from src.application.use_cases.purge_expired_links import PurgeExpiredLinksUseCase
        from src.application.services.time_provider import SystemTimeProvider

        # Create a link via API
        payload = {
            "original_url": "https://example.com",
            "custom_alias": "purgecachetest"
        }
        response = await client.post("/links/shorten", json=payload)
        assert response.status_code == 201
        short_code = response.json()["short_code"]

        # Populate cache by redirecting
        await client.get(f"/opupupa/{short_code}", follow_redirects=False)

        # Reset mocks
        redis_client.client.delete.reset_mock()

        # Manually mark link as expired in database
        # We need to get the link from DB and update its expiration to past
        async with uow:
            link = await uow.links.get_by_short_code(short_code)
            # Set expires_at to past
            past_time = datetime.now(timezone.utc).replace(microsecond=0)
            from src.domain.value_objects.expires_at import ExpiresAt
            link.update_expires_at(ExpiresAt.from_datetime(past_time))
            await uow.links.update(link)
            await uow.commit()


        # Assert: cache.invalidate was called for each purged link
        # Note: The purge job would call cache.invalidate, but the use case doesn't.
        # The purge job integration is tested separately.
        # For this test, we need to verify that the purge job's cache invalidation works.
        # Since purge job is mocked, we'll test the integration by patching.
        # Let's directly test the purge job's _purge_batch method.
        from src.infrastructure.jobs.purge_expired_links_job import PurgeExpiredLinksJob
        from src.infrastructure.cache.link_cache import LinkCache

        cache = LinkCache()
        cache._redis = redis_client

        job = PurgeExpiredLinksJob(
            uow_factory=lambda: uow,
            cache=cache,
            interval_sec=3600,
        )

        # Reset delete mock because we already used it above
        redis_client.client.delete.reset_mock()

        await job._purge_batch()

        # Assert cache invalidation was called
        redis_client.client.delete.assert_called_once_with(f"link:code:{short_code}")